import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from tecnosupply.config import RUTA_MEMORIA


def crear_checkpointer() -> SqliteSaver:
    """Construye la memoria persistente del agente en SQLite."""
    conexion = sqlite3.connect(
        RUTA_MEMORIA,
        check_same_thread=False,
    )

    return SqliteSaver(conexion)