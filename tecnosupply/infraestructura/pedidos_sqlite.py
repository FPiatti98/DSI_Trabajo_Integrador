import sqlite3
from contextlib import closing

from tecnosupply.config import RUTA_BD_OPERACIONES


def obtener_pedido(numero_pedido: str) -> dict[str, str] | None:
    """
    Consulta un pedido por su identificador.

    Devuelve sus datos o None si no existe.
    Abre la base en modo de solo lectura.
    """
    ruta_sqlite = RUTA_BD_OPERACIONES.as_uri() + "?mode=ro"

    with closing(
        sqlite3.connect(ruta_sqlite, uri=True)
    ) as conexion:
        conexion.row_factory = sqlite3.Row

        pedido = conexion.execute(
            """
            SELECT
                numero_pedido,
                estado,
                producto,
                fecha_actualizacion
            FROM pedidos
            WHERE numero_pedido = ?
            """,
            (numero_pedido,),
        ).fetchone()

    return dict(pedido) if pedido is not None else None