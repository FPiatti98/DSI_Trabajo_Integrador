import json
from typing import Any

from langchain_core.tools import tool

from tecnosupply.aplicacion.servicio_conocimiento import (
    consultar_conocimiento,
)
from tecnosupply.aplicacion.servicio_operaciones import (
    consultar_pedido,
    crear_reclamo,
)
from tecnosupply.dominio.reglas_reclamos import ErrorReglaNegocio


def convertir_a_json(datos: dict[str, Any]) -> str:
    """Serializa el resultado de un servicio conservando las tildes."""
    return json.dumps(datos, ensure_ascii=False)


@tool
def buscar_conocimiento(consulta: str) -> str:
    """
    Busca información vigente en la base de conocimiento de TecnoSupply.

    Debe utilizarse para consultas generales de soporte, facturación,
    envíos, garantías, stock, pagos o procedimientos de reclamos.

    Args:
        consulta: Pregunta del usuario en lenguaje natural.

    Returns:
        JSON con hasta tres documentos vigentes, sus identificadores,
        metadatos, distancias y contenido, o un error.

    Safety:
        Solo recupera información. No modifica operaciones.
    """
    try:
        resultado = consultar_conocimiento(consulta)
    except ValueError as error:
        return convertir_a_json({"error": str(error)})
    except Exception as error:
        return convertir_a_json(
            {
                "error": (
                    "No fue posible consultar "
                    "la base de conocimiento local."
                ),
                "detalle": str(error),
            }
        )

    return convertir_a_json(resultado)


@tool
def consultar_estado_pedido(numero_pedido: str) -> str:
    """
    Consulta el estado operativo actual de un pedido de TecnoSupply.

    Funciona como sensor del dominio y debe utilizarse para conocer
    el estado logístico de un pedido identificado.

    Args:
        numero_pedido: Identificador del pedido, por ejemplo PED-1003.

    Returns:
        JSON con pedido, estado, producto y fecha de actualización,
        o un error si el identificador no corresponde a un pedido.

    Safety:
        Es una operación de lectura. No modifica pedidos ni reclamos.
    """
    try:
        resultado = consultar_pedido(numero_pedido)
    except ErrorReglaNegocio as error:
        return convertir_a_json(
            {
                "error": str(error),
                "sugerencia": (
                    "Verifique el formato. Ejemplo válido: PED-1001."
                ),
            }
        )

    return convertir_a_json(resultado)


@tool
def registrar_reclamo(
    numero_pedido: str,
    descripcion: str,
) -> str:
    """
    Registra un reclamo de postventa asociado a un pedido existente.

    Debe utilizarse cuando el usuario solicita explícitamente iniciar
    un reclamo e informa el pedido y una descripción del problema.

    Args:
        numero_pedido: Identificador del pedido afectado.
        descripcion: Descripción concreta del inconveniente.

    Returns:
        JSON con identificador del reclamo, pedido, estado inicial,
        fecha de creación y aclaración comercial, o un error.

    Safety:
        Crea un registro persistente. No aprueba devoluciones,
        reemplazos ni reintegros.
    """
    try:
        resultado = crear_reclamo(
            numero_pedido=numero_pedido,
            descripcion=descripcion,
        )
    except ErrorReglaNegocio as error:
        return convertir_a_json({"error": str(error)})

    return convertir_a_json(resultado)


HERRAMIENTAS = [
    buscar_conocimiento,
    consultar_estado_pedido,
    registrar_reclamo,
]


if __name__ == "__main__":
    print("Herramientas disponibles:")

    for herramienta in HERRAMIENTAS:
        print(
            f"- {herramienta.name}: "
            f"{herramienta.description.splitlines()[0]}"
        )