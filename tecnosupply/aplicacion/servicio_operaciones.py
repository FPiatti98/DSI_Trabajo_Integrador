from tecnosupply.dominio.reglas_reclamos import (
    ErrorReglaNegocio,
    validar_datos_reclamo,
)
from tecnosupply.infraestructura.pedidos_sqlite import obtener_pedido
from tecnosupply.infraestructura.reclamos_sqlite import insertar_reclamo


def consultar_pedido(numero_pedido: str) -> dict[str, str]:
    """Valida el identificador y consulta un pedido existente."""
    numero_normalizado = numero_pedido.strip().upper()

    if not numero_normalizado:
        raise ErrorReglaNegocio(
            "Debe indicar un número de pedido."
        )

    pedido = obtener_pedido(numero_normalizado)

    if pedido is None:
        raise ErrorReglaNegocio(
            f"No se encontró el pedido {numero_normalizado}."
        )

    return pedido


def crear_reclamo(
    numero_pedido: str,
    descripcion: str,
) -> dict[str, str | int]:
    """
    Coordina el registro de un reclamo.

    Valida los datos, comprueba que exista el pedido y solicita
    su almacenamiento con estado inicial abierto.
    """
    numero_normalizado, descripcion_normalizada = validar_datos_reclamo(
        numero_pedido,
        descripcion,
    )

    pedido = obtener_pedido(numero_normalizado)

    if pedido is None:
        raise ErrorReglaNegocio(
            "No se puede registrar el reclamo porque "
            f"el pedido {numero_normalizado} no existe."
        )

    reclamo = insertar_reclamo(
        numero_pedido=numero_normalizado,
        descripcion=descripcion_normalizada,
        estado="abierto",
    )

    return {
        "mensaje": "Reclamo registrado correctamente.",
        "id_reclamo": reclamo["id_reclamo"],
        "numero_pedido": reclamo["numero_pedido"],
        "estado": reclamo["estado"],
        "fecha_creacion_utc": reclamo["fecha_creacion_utc"],
        "aclaracion": (
            "El registro no implica aprobación automática de devolución, "
            "reemplazo ni reintegro."
        ),
    }