from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

CARPETA_ENTREGA_4 = Path(__file__).resolve().parent
RAIZ_PROYECTO = CARPETA_ENTREGA_4.parent

load_dotenv(RAIZ_PROYECTO / ".env", override=True)

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "tecnosupply-agente-entrega4"
if os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

try:
    from .agente import (
        MODELO_OLLAMA,
        RUTA_MEMORIA,
        consultar_agente_detallado,
        obtener_historial,
    )
    from .observabilidad import (
        inicializar_observabilidad,
        obtener_metricas,
        registrar_consulta,
        registrar_log_json,
    )
except ImportError:
    from agente import (
        MODELO_OLLAMA,
        RUTA_MEMORIA,
        consultar_agente_detallado,
        obtener_historial,
    )
    from observabilidad import (
        inicializar_observabilidad,
        obtener_metricas,
        registrar_consulta,
        registrar_log_json,
    )

RUTA_BD_OPERACIONES = CARPETA_ENTREGA_4 / "operaciones.db"
RUTA_CHROMA_OLLAMA = CARPETA_ENTREGA_4 / "chroma_ollama"

app = FastAPI(
    title="API del Agente TecnoSupply",
    description=(
        "API REST para consultar un agente ReAct con herramientas, "
        "memoria SQLite, recuperación RAG local y observabilidad."
    ),
    version="1.0.0",
)


class ConsultaRequest(BaseModel):
    """Cuerpo esperado por el endpoint POST /consultar."""

    consulta: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Consulta del usuario en lenguaje natural.",
    )
    thread_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Identificador persistente de la conversación.",
    )


class ConsultaResponse(BaseModel):
    """Respuesta generada por el agente."""

    thread_id: str
    respuesta: str
    herramientas_usadas: list[str]


class EstadoResponse(BaseModel):
    """Estado e historial visible de una conversación."""

    thread_id: str
    cantidad_mensajes: int
    historial: list[dict[str, str]]


@app.on_event("startup")
def iniciar_observabilidad() -> None:
    """Inicializa los recursos de observabilidad al arrancar la API."""
    inicializar_observabilidad()

    registrar_log_json(
        "api_iniciada",
        modelo=MODELO_OLLAMA,
        proyecto_langsmith=os.environ["LANGSMITH_PROJECT"],
    )


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Verifica que los recursos locales principales estén disponibles."""
    return {
        "estado": "ok",
        "modelo": MODELO_OLLAMA,
        "memoria_sqlite": RUTA_MEMORIA.exists(),
        "base_operaciones": RUTA_BD_OPERACIONES.exists(),
        "chroma_local": RUTA_CHROMA_OLLAMA.exists(),
    }


@app.post("/consultar", response_model=ConsultaResponse)
def consultar(datos: ConsultaRequest) -> ConsultaResponse:
    """Envía una consulta al agente y registra métricas de la ejecución."""
    inicio = perf_counter()

    try:
        resultado = consultar_agente_detallado(
            consulta=datos.consulta,
            thread_id=datos.thread_id,
        )

        latencia_ms = (perf_counter() - inicio) * 1000
        herramientas = resultado["herramientas"]

        registrar_consulta(
            thread_id=datos.thread_id,
            consulta=datos.consulta,
            latencia_ms=latencia_ms,
            estado="ok",
            herramientas=herramientas,
        )

        return ConsultaResponse(
            thread_id=datos.thread_id,
            respuesta=str(resultado["respuesta"]),
            herramientas_usadas=herramientas,
        )

    except ValueError as error:
        latencia_ms = (perf_counter() - inicio) * 1000

        registrar_consulta(
            thread_id=datos.thread_id,
            consulta=datos.consulta,
            latencia_ms=latencia_ms,
            estado="error",
            detalle_error=str(error),
        )

        raise HTTPException(status_code=400, detail=str(error)) from error

    except Exception as error:
        latencia_ms = (perf_counter() - inicio) * 1000

        registrar_consulta(
            thread_id=datos.thread_id,
            consulta=datos.consulta,
            latencia_ms=latencia_ms,
            estado="error",
            detalle_error=type(error).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail="No fue posible procesar la consulta del agente.",
        ) from error


@app.get("/estado/{thread_id}", response_model=EstadoResponse)
def estado(thread_id: str) -> EstadoResponse:
    """Devuelve el historial visible asociado a un thread_id."""
    try:
        historial = obtener_historial(thread_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="No fue posible recuperar el estado de la conversación.",
        ) from error

    return EstadoResponse(
        thread_id=thread_id,
        cantidad_mensajes=len(historial),
        historial=historial,
    )


@app.get("/metricas")
def metricas() -> dict:
    """
    Devuelve consultas, errores, bloqueos, latencia promedio, p95 y frecuencia
    de uso de herramientas.
    """
    return obtener_metricas()