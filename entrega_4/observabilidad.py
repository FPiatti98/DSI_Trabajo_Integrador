from __future__ import annotations

import json
import sqlite3
import threading
from collections import Counter
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any

CARPETA_ENTREGA_4 = Path(__file__).resolve().parent
CARPETA_LOGS = CARPETA_ENTREGA_4 / "logs"
RUTA_LOG_JSON = CARPETA_LOGS / "agente.jsonl"
RUTA_BD_METRICAS = CARPETA_ENTREGA_4 / "observabilidad.sqlite"

LOCK_LOGS = threading.Lock()


def fecha_utc() -> str:
    """Devuelve la fecha actual en formato ISO UTC."""
    return datetime.now(timezone.utc).isoformat()


def obtener_conexion() -> sqlite3.Connection:
    """Abre una conexión SQLite para las métricas del agente."""
    conexion = sqlite3.connect(RUTA_BD_METRICAS)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_observabilidad() -> None:
    """Crea la carpeta de logs y la tabla persistente de métricas."""
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)

    with obtener_conexion() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_utc TEXT NOT NULL,
                thread_id TEXT,
                longitud_consulta INTEGER NOT NULL,
                latencia_ms REAL NOT NULL,
                estado TEXT NOT NULL,
                herramientas_json TEXT NOT NULL,
                bloqueado INTEGER NOT NULL DEFAULT 0,
                detalle_error TEXT
            )
            """
        )


def registrar_log_json(evento: str, **datos: Any) -> None:
    """
    Escribe un evento estructurado en formato JSON Lines.

    Cada línea del archivo representa un evento independiente y puede
    procesarse luego mediante herramientas de análisis de logs.
    """
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)

    registro = {
        "timestamp_utc": fecha_utc(),
        "evento": evento,
        **datos,
    }

    with LOCK_LOGS:
        with RUTA_LOG_JSON.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def registrar_consulta(
    *,
    thread_id: str,
    consulta: str,
    latencia_ms: float,
    estado: str,
    herramientas: list[str] | None = None,
    bloqueado: bool = False,
    detalle_error: str | None = None,
) -> None:
    """
    Registra una consulta procesada en el log JSON y en SQLite.

    Args:
        thread_id: Identificador de la conversación.
        consulta: Texto de la consulta, usado solo para medir longitud.
        latencia_ms: Duración total de procesamiento en milisegundos.
        estado: Resultado de la operación, por ejemplo `ok`, `error` o `bloqueado`.
        herramientas: Herramientas utilizadas por el agente.
        bloqueado: Indica si un guardrail bloqueó la consulta.
        detalle_error: Motivo resumido del error o bloqueo, si existe.
    """
    herramientas = herramientas or []

    registro = {
        "thread_id": thread_id,
        "longitud_consulta": len(consulta),
        "latencia_ms": round(latencia_ms, 2),
        "estado": estado,
        "herramientas": herramientas,
        "bloqueado": bloqueado,
        "detalle_error": detalle_error,
    }

    registrar_log_json("consulta_procesada", **registro)

    with obtener_conexion() as conexion:
        conexion.execute(
            """
            INSERT INTO consultas (
                fecha_utc,
                thread_id,
                longitud_consulta,
                latencia_ms,
                estado,
                herramientas_json,
                bloqueado,
                detalle_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fecha_utc(),
                thread_id,
                len(consulta),
                latencia_ms,
                estado,
                json.dumps(herramientas, ensure_ascii=False),
                int(bloqueado),
                detalle_error,
            ),
        )


def calcular_percentil_95(latencias: list[float]) -> float:
    """Calcula p95 usando el método de rango más cercano."""
    if not latencias:
        return 0.0

    valores = sorted(latencias)
    indice = ceil(0.95 * len(valores)) - 1

    return round(valores[indice], 2)


def obtener_metricas() -> dict[str, Any]:
    """
    Devuelve métricas agregadas persistidas desde SQLite.

    Incluye cantidad de consultas, errores, bloqueos, latencia promedio,
    p95 de latencia y frecuencia de uso de herramientas.
    """
    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT
                latencia_ms,
                estado,
                herramientas_json,
                bloqueado
            FROM consultas
            ORDER BY id
            """
        ).fetchall()

    total_consultas = len(filas)
    errores = sum(1 for fila in filas if fila["estado"] == "error")
    bloqueos = sum(1 for fila in filas if fila["bloqueado"] == 1)

    latencias = [
        float(fila["latencia_ms"])
        for fila in filas
        if fila["estado"] == "ok"
    ]

    contador_herramientas: Counter[str] = Counter()

    for fila in filas:
        try:
            herramientas = json.loads(fila["herramientas_json"])
        except json.JSONDecodeError:
            herramientas = []

        contador_herramientas.update(herramientas)

    latencia_promedio = (
        round(sum(latencias) / len(latencias), 2) if latencias else 0.0
    )

    return {
        "consultas": total_consultas,
        "errores": errores,
        "bloqueos": bloqueos,
        "latencia_promedio_ms": latencia_promedio,
        "latencia_p95_ms": calcular_percentil_95(latencias),
        "herramientas": dict(contador_herramientas),
    }