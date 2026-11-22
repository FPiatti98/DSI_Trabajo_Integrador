import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from tecnosupply.config import RUTA_BD_OPERACIONES


def insertar_reclamo(
    numero_pedido: str,
    descripcion: str,
    estado: str,
) -> dict[str, str | int]:
    """
    Guarda un reclamo en SQLite y devuelve sus datos.

    Recibe los datos ya validados y el estado decidido por la aplicación.
    La transacción confirma la escritura o la revierte si ocurre un error.
    """
    fecha_creacion = datetime.now(timezone.utc).isoformat()
    ruta_sqlite = RUTA_BD_OPERACIONES.as_uri() + "?mode=rw"

    with closing(
        sqlite3.connect(ruta_sqlite, uri=True)
    ) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")

        with conexion:
            cursor = conexion.execute(
                """
                INSERT INTO reclamos (
                    numero_pedido,
                    descripcion,
                    estado,
                    fecha_creacion
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    numero_pedido,
                    descripcion,
                    estado,
                    fecha_creacion,
                ),
            )

            identificador = cursor.lastrowid

            if identificador is None:
                raise RuntimeError(
                    "No se obtuvo el identificador del reclamo."
                )

    return {
        "id_reclamo": identificador,
        "numero_pedido": numero_pedido,
        "descripcion": descripcion,
        "estado": estado,
        "fecha_creacion_utc": fecha_creacion,
    }