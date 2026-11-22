import sqlite3
from contextlib import closing

from tecnosupply.config import RUTA_BD_OPERACIONES


PEDIDOS_DEMO = [
    (
        "PED-1001",
        "confirmado",
        "Notebook Lenovo ThinkPad E14",
        "2026-11-01 10:30",
    ),
    (
        "PED-1002",
        "despachado",
        "Monitor Samsung 24 pulgadas",
        "2026-11-02 14:15",
    ),
    (
        "PED-1003",
        "en tránsito",
        "Mouse Logitech MX Master",
        "2026-11-03 09:40",
    ),
    (
        "PED-1004",
        "entregado",
        "Notebook ASUS Vivobook",
        "2026-11-04 16:20",
    ),
]


def inicializar_base_operaciones() -> None:
    """
    Crea las tablas necesarias y carga los pedidos de demostración.

    Conserva los registros existentes: no borra ni reemplaza pedidos
    o reclamos almacenados.
    """
    with closing(
        sqlite3.connect(RUTA_BD_OPERACIONES)
    ) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")

        with conexion:
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS pedidos (
                    numero_pedido TEXT PRIMARY KEY,
                    estado TEXT NOT NULL,
                    producto TEXT NOT NULL,
                    fecha_actualizacion TEXT NOT NULL
                )
                """
            )

            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS reclamos (
                    id_reclamo INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_pedido TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    fecha_creacion TEXT NOT NULL,
                    FOREIGN KEY (numero_pedido)
                        REFERENCES pedidos(numero_pedido)
                )
                """
            )

            conexion.executemany(
                """
                INSERT OR IGNORE INTO pedidos (
                    numero_pedido,
                    estado,
                    producto,
                    fecha_actualizacion
                )
                VALUES (?, ?, ?, ?)
                """,
                PEDIDOS_DEMO,
            )