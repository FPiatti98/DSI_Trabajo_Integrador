from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

from herramientas import HERRAMIENTAS, inicializar_base_operaciones

CARPETA_ENTREGA_4 = Path(__file__).resolve().parent
RUTA_MEMORIA = CARPETA_ENTREGA_4 / "memoria_agente.sqlite"

MODELO_OLLAMA = "qwen3:4b-instruct"
URL_OLLAMA = "http://localhost:11434"
LIMITE_ITERACIONES = 8

INSTRUCCIONES_SISTEMA = """
Sos el agente de atención al cliente de TecnoSupply Argentina.

Tu objetivo es responder consultas usando las herramientas disponibles y nunca
inventar datos, políticas, estados de pedidos ni acciones realizadas.

Regla obligatoria de uso de herramientas:
- Antes de responder una consulta sobre TecnoSupply, debés usar al menos una
  herramienta adecuada. No respondas directamente usando conocimiento general.
- Para preguntas de soporte, facturación, envíos, garantías, stock, pagos o
  reclamos generales, llamá siempre a buscar_conocimiento antes de responder.
- Para preguntas sobre un pedido identificado, llamá siempre a
  consultar_estado_pedido antes de responder.
- Si la consulta pide iniciar un reclamo y contiene pedido y descripción,
  llamá a registrar_reclamo antes de responder.
- Solo podés responder sin herramientas a saludos o mensajes que no sean una
  consulta sobre TecnoSupply.

Reglas para decidir qué herramienta usar:
- Para políticas, soporte, facturación, garantías, envíos, pagos, stock o
  reclamos generales, usá buscar_conocimiento.
- Para conocer el estado real de un pedido, usá consultar_estado_pedido.
- Para registrar un reclamo, usá registrar_reclamo solo si el usuario expresa
  claramente que desea iniciarlo y brinda número de pedido y descripción.
- Registrar un reclamo no autoriza devoluciones, reemplazos ni reintegros.
- La conversación se conserva dentro del mismo thread_id. Si el usuario pide
  recordar un dato, confirmá que lo usarás en los próximos turnos de esa
  conversación. No afirmes que no podés recordar información.

Reglas estrictas de fundamentación:
- La salida de una herramienta es la única fuente de verdad.
- Cuando usar buscar_conocimiento, respondé únicamente con información
  explícita en el campo contenido de los documentos recuperados.
- No agregues pasos, componentes, plazos, promesas o requisitos que no estén
  escritos en la herramienta.
- Para una notebook que no enciende, si el documento menciona cargador,
  conexión eléctrica e indicadores luminosos, limitate exactamente a esos
  controles. No menciones botón de encendido, batería, sistema operativo ni
  otras verificaciones si no aparecen en la evidencia.
- No prometas acciones futuras, por ejemplo "te mantendré informado".
- Si falta información necesaria, pedila al usuario.
- Si la información no está disponible, respondé que no contás con datos
  suficientes. No supongas ni completes datos faltantes.
- Respondé siempre en español argentino, de forma clara y breve.
"""


def crear_modelo() -> ChatOllama:
    """
    Crea el modelo local de Ollama para razonar y decidir qué herramienta usar.

    Returns:
        Instancia local de ChatOllama con el modelo qwen3:4b-instruct.
    """
    return ChatOllama(
        model=MODELO_OLLAMA,
        base_url=URL_OLLAMA,
        temperature=0,
    )


def crear_checkpointer() -> SqliteSaver:
    """
    Crea un checkpointer SQLite persistente para la memoria conversacional.

    Cada conversación se diferencia mediante thread_id. Por eso, el agente puede
    recuperar mensajes anteriores incluso luego de reiniciar el proceso.

    Returns:
        Checkpointer SQLite conectado a memoria_agente.sqlite.
    """
    conexion = sqlite3.connect(RUTA_MEMORIA, check_same_thread=False)
    return SqliteSaver(conexion)


def crear_agente():
    """
    Construye el grafo ReAct de LangGraph.

    El agente alterna entre el modelo y las herramientas hasta generar una
    respuesta final. El límite de pasos se configura al invocarlo mediante
    recursion_limit.

    Returns:
        Grafo ReAct compilado con herramientas y memoria SQLite persistente.
    """
    inicializar_base_operaciones()

    return create_react_agent(
        model=crear_modelo(),
        tools=HERRAMIENTAS,
        prompt=INSTRUCCIONES_SISTEMA,
        checkpointer=crear_checkpointer(),
    )


AGENTE = crear_agente()


def convertir_contenido_a_texto(contenido: Any) -> str:
    """Convierte contenido de mensajes de LangChain a texto legible."""
    if isinstance(contenido, str):
        return contenido

    if isinstance(contenido, list):
        partes = []

        for item in contenido:
            if isinstance(item, dict):
                partes.append(str(item.get("text", item)))
            else:
                partes.append(str(item))

        return "\n".join(partes)

    return str(contenido)


def construir_respuesta_fundamentada(
    mensajes_nuevos: list[BaseMessage],
    respuesta_modelo: str,
) -> str:
    """
    Construye una respuesta segura a partir de la última herramienta usada.

    Evita que el modelo agregue instrucciones, políticas o promesas que no
    figuren en la salida de la herramienta.
    """
    for mensaje in reversed(mensajes_nuevos):
        if not isinstance(mensaje, ToolMessage):
            continue

        try:
            datos = json.loads(str(mensaje.content))
        except json.JSONDecodeError:
            continue

        if mensaje.name == "buscar_conocimiento":
            resultados = datos.get("resultados", [])

            if resultados:
                contenido = resultados[0].get("contenido", "").strip()

                if contenido:
                    return (
                        "Según la base de conocimiento de TecnoSupply:\n\n"
                        f"{contenido}"
                    )

        if mensaje.name == "consultar_estado_pedido":
            if "error" not in datos:
                return (
                    f"El pedido {datos['numero_pedido']} se encuentra "
                    f"{datos['estado']}. El producto es "
                    f"{datos['producto']}. La última actualización fue "
                    f"{datos['fecha_actualizacion']}."
                )

        if mensaje.name == "registrar_reclamo":
            if "error" not in datos:
                return (
                    f"{datos['mensaje']} Número de reclamo: "
                    f"{datos['id_reclamo']}. Estado: {datos['estado']}. "
                    f"{datos['aclaracion']}"
                )

    return respuesta_modelo


def consultar_agente(consulta: str, thread_id: str) -> str:
    """
    Ejecuta una consulta en el agente usando memoria asociada al thread_id.

    Args:
        consulta: Mensaje actual del usuario.
        thread_id: Identificador estable de la conversación.

    Returns:
        Respuesta final validada y fundamentada en herramientas.

    Raises:
        ValueError: Si la consulta o el thread_id están vacíos.
    """
    consulta = consulta.strip()
    thread_id = thread_id.strip()

    if not consulta:
        raise ValueError("La consulta no puede estar vacía.")

    if not thread_id:
        raise ValueError("El thread_id no puede estar vacío.")

    configuracion = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": LIMITE_ITERACIONES,
    }

    estado_previo = AGENTE.get_state(configuracion)
    cantidad_mensajes_previos = len(
        estado_previo.values.get("messages", [])
    )

    resultado = AGENTE.invoke(
        {"messages": [HumanMessage(content=consulta)]},
        config=configuracion,
    )

    mensajes = resultado["messages"]
    mensajes_nuevos = mensajes[cantidad_mensajes_previos:]
    respuesta_final = mensajes[-1]

    if not isinstance(respuesta_final, AIMessage):
        raise RuntimeError("El agente no devolvió un mensaje final del asistente.")

    respuesta_modelo = convertir_contenido_a_texto(respuesta_final.content)

    return construir_respuesta_fundamentada(
        mensajes_nuevos,
        respuesta_modelo,
    )


def obtener_historial(thread_id: str) -> list[dict[str, str]]:
    """
    Recupera el historial persistido de una conversación.

    Las respuestas que siguieron al uso de herramientas se reconstruyen desde
    esas herramientas para no exponer reformulaciones no fundamentadas del LLM.

    Args:
        thread_id: Identificador de la conversación a consultar.

    Returns:
        Lista de mensajes visibles del usuario y del asistente.
    """
    thread_id = thread_id.strip()

    if not thread_id:
        raise ValueError("El thread_id no puede estar vacío.")

    configuracion = {"configurable": {"thread_id": thread_id}}
    estado = AGENTE.get_state(configuracion)
    mensajes: list[BaseMessage] = estado.values.get("messages", [])

    historial: list[dict[str, str]] = []
    herramientas_turno: list[BaseMessage] = []

    for mensaje in mensajes:
        tipo = getattr(mensaje, "type", "desconocido")

        if tipo == "human":
            herramientas_turno = []
            contenido = convertir_contenido_a_texto(mensaje.content).strip()

            if contenido:
                historial.append(
                    {
                        "rol": "usuario",
                        "contenido": contenido,
                    }
                )

            continue

        if tipo == "tool":
            herramientas_turno.append(mensaje)
            continue

        if tipo == "ai":
            contenido_modelo = convertir_contenido_a_texto(
                mensaje.content
            ).strip()

            # Mensaje intermedio que solo solicita una herramienta.
            if not contenido_modelo and not herramientas_turno:
                continue

            contenido = construir_respuesta_fundamentada(
                herramientas_turno,
                contenido_modelo,
            ).strip()

            if contenido:
                historial.append(
                    {
                        "rol": "asistente",
                        "contenido": contenido,
                    }
                )

            herramientas_turno = []

    return historial


if __name__ == "__main__":
    THREAD_DEMO = "demo-ollama-memoria-002"

    print("=== Prueba de agente local con Ollama y memoria SQLite ===\n")

    respuesta_1 = consultar_agente(
        "Quiero saber el estado del pedido PED-1001.",
        THREAD_DEMO,
    )
    print("Usuario: Quiero saber el estado del pedido PED-1001.\n")
    print(f"Agente: {respuesta_1}\n")

    respuesta_2 = consultar_agente(
        "¿Cuál era el producto de ese pedido?",
        THREAD_DEMO,
    )
    print("Usuario: ¿Cuál era el producto de ese pedido?\n")
    print(f"Agente: {respuesta_2}\n")

    print("=== Historial persistido ===")
    for mensaje in obtener_historial(THREAD_DEMO):
        print(f"{mensaje['rol'].capitalize()}: {mensaje['contenido']}")