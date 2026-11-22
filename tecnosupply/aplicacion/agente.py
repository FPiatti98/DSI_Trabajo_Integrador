from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from tecnosupply.config import (
    LIMITE_ITERACIONES,
    MODELO_OLLAMA,
    RUTA_MEMORIA,
    URL_OLLAMA,
)
from tecnosupply.aplicacion.contexto_conversacion import resolver_referencia_pedido
from tecnosupply.aplicacion.herramientas import (
    HERRAMIENTAS,
    buscar_conocimiento,
    consultar_estado_pedido,
)
from tecnosupply.infraestructura.base_operaciones import (
    inicializar_base_operaciones,
)
from tecnosupply.infraestructura.memoria_sqlite import crear_checkpointer
from tecnosupply.infraestructura.ollama import crear_modelo


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

Reglas estrictas de fundamentación:
- La salida de una herramienta es la única fuente de verdad.
- Cuando usar buscar_conocimiento, respondé únicamente con información
  explícita en el campo contenido de los documentos recuperados.
- No agregues pasos, componentes, plazos, promesas o requisitos que no estén
  escritos en la herramienta.
- No prometas acciones futuras, por ejemplo "te mantendré informado".
- Si falta información necesaria, pedila al usuario.
- Si la información no está disponible, respondé que no contás con datos
  suficientes. No supongas ni completes datos faltantes.
- Respondé siempre en español argentino, de forma clara y breve.
"""


def crear_agente():
    """Construye el grafo ReAct con herramientas y memoria SQLite."""
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


def ejecutar_fallback_lectura(consulta: str) -> ToolMessage:
    """
    Ejecuta una herramienta de solo lectura si el modelo no llamó ninguna.

    Este fallback evita respuestas no fundamentadas de modelos locales pequeños.
    Nunca ejecuta el actuador registrar_reclamo, ya que una acción con efectos
    persistentes requiere una decisión explícita del agente.
    """
    coincidencia_pedido = re.search(r"\bPED-\d+\b", consulta.upper())

    if coincidencia_pedido:
        numero_pedido = coincidencia_pedido.group(0)

        contenido = consultar_estado_pedido.invoke(
            {"numero_pedido": numero_pedido}
        )

        return ToolMessage(
            content=contenido,
            name="consultar_estado_pedido",
            tool_call_id="fallback_lectura",
        )

    contenido = buscar_conocimiento.invoke({"consulta": consulta})

    return ToolMessage(
        content=contenido,
        name="buscar_conocimiento",
        tool_call_id="fallback_lectura",
    )


def construir_respuesta_fundamentada(
    mensajes_nuevos: list[BaseMessage],
    respuesta_modelo: str,
) -> str:
    """
    Construye una respuesta segura desde la última salida de herramienta.

    Evita que el modelo agregue instrucciones, políticas o promesas que no
    figuren en la salida estructurada.
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


def consultar_agente_detallado(
    consulta: str,
    thread_id: str,
) -> dict[str, Any]:
    """
    Ejecuta una consulta y devuelve respuesta más herramientas utilizadas.

    Si el modelo no usa ninguna herramienta de lectura, aplica un fallback
    seguro para evitar respuestas sin evidencia.

    Returns:
        Diccionario con respuesta fundamentada y herramientas ejecutadas.
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
    mensajes_previos = estado_previo.values.get("messages", [])
    cantidad_mensajes_previos = len(mensajes_previos)
    consulta_contextual = resolver_referencia_pedido(
        consulta,
        (
            convertir_contenido_a_texto(mensaje.content)
            for mensaje in mensajes_previos
            if isinstance(mensaje, HumanMessage)
        ),
    )
    metadatos_consulta = (
        {"consulta_original": consulta} if consulta_contextual != consulta else {}
    )

    resultado = AGENTE.invoke(
        {"messages": [HumanMessage(
            content=consulta_contextual,
            additional_kwargs=metadatos_consulta,
        )]},
        config=configuracion,
    )

    mensajes = resultado["messages"]
    mensajes_nuevos = mensajes[cantidad_mensajes_previos:]
    respuesta_final = mensajes[-1]

    if not isinstance(respuesta_final, AIMessage):
        raise RuntimeError("El agente no devolvió un mensaje final del asistente.")

    respuesta_modelo = convertir_contenido_a_texto(respuesta_final.content)

    herramientas_usadas = [
        mensaje.name
        for mensaje in mensajes_nuevos
        if isinstance(mensaje, ToolMessage)
    ]

    # Qwen3 puede omitir una herramienta en ciertas consultas. Se habilita
    # únicamente un fallback de lectura, nunca una acción persistente.
    if not herramientas_usadas:
        mensaje_fallback = ejecutar_fallback_lectura(consulta_contextual)
        mensajes_nuevos.append(mensaje_fallback)
        herramientas_usadas = [mensaje_fallback.name]

    respuesta = construir_respuesta_fundamentada(
        mensajes_nuevos,
        respuesta_modelo,
    )

    return {
        "respuesta": respuesta,
        "herramientas": herramientas_usadas,
    }


def consultar_agente(consulta: str, thread_id: str) -> str:
    """Ejecuta una consulta y devuelve únicamente la respuesta final."""
    resultado = consultar_agente_detallado(
        consulta=consulta,
        thread_id=thread_id,
    )

    return str(resultado["respuesta"])


def obtener_historial(thread_id: str) -> list[dict[str, str]]:
    """
    Recupera el historial visible persistido de una conversación.

    Las respuestas posteriores a herramientas se reconstruyen desde la salida
    estructurada para no exponer reformulaciones no fundamentadas del modelo.
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
            contenido = convertir_contenido_a_texto(
                mensaje.additional_kwargs.get("consulta_original", mensaje.content)
            ).strip()

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
    THREAD_DEMO = "demo-ollama-memoria-004"

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
