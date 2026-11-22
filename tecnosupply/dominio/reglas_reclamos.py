class ErrorReglaNegocio(ValueError):
    """Indica que una operación no cumple una regla del negocio."""


LONGITUD_MINIMA_DESCRIPCION = 10


def validar_datos_reclamo(
    numero_pedido: str,
    descripcion: str,
) -> tuple[str, str]:
    """
    Valida y normaliza los datos necesarios para registrar un reclamo.

    No consulta bases de datos ni registra operaciones.
    La existencia del pedido se comprobará por separado.
    """
    numero_normalizado = numero_pedido.strip().upper()
    descripcion_normalizada = descripcion.strip()

    if not numero_normalizado:
        raise ErrorReglaNegocio(
            "Debe indicar el número de pedido para registrar el reclamo."
        )

    if len(descripcion_normalizada) < LONGITUD_MINIMA_DESCRIPCION:
        raise ErrorReglaNegocio(
            "La descripción es demasiado breve. "
            "Indique qué producto presenta el problema y qué ocurrió."
        )

    return numero_normalizado, descripcion_normalizada