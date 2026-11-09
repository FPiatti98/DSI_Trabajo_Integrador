from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from .agente import (
        MODELO_OLLAMA,
        RUTA_MEMORIA,
        consultar_agente,
        obtener_historial,
    )
except ImportError:
    from agente import (
        MODELO_OLLAMA,
        RUTA_MEMORIA,
        consultar_agente,
        obtener_historial,
    )

CARPETA_ENTREGA_4 = Path(__file__).resolve().parent
RUTA_BD_OPERACIONES = CARPETA_ENTREGA_4 / "operaciones.db"
RUTA_CHROMA_OLLAMA = CARPETA_ENTREGA_4 / "chroma_ollama"

app = FastAPI(
    title="API del Agente TecnoSupply",
    description=(
        "API REST para consultar un agente ReAct con herramientas, "
        "memoria SQLite y recuperación RAG local."
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


class EstadoResponse(BaseModel):
    """Estado e historial visible de una conversación."""

    thread_id: str
    cantidad_mensajes: int
    historial: list[dict[str, str]]


@app.get("/health")
def health() -> dict[str, str | bool]:
    """
    Verifica que los recursos locales principales del sistema estén disponibles.
    """
    return {
        "estado": "ok",
        "modelo": MODELO_OLLAMA,
        "memoria_sqlite": RUTA_MEMORIA.exists(),
        "base_operaciones": RUTA_BD_OPERACIONES.exists(),
        "chroma_local": RUTA_CHROMA_OLLAMA.exists(),
    }


@app.post("/consultar", response_model=ConsultaResponse)
def consultar(datos: ConsultaRequest) -> ConsultaResponse:
    """
    Envía una consulta al agente y conserva la memoria según el thread_id.
    """
    try:
        respuesta = consultar_agente(
            consulta=datos.consulta,
            thread_id=datos.thread_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="No fue posible procesar la consulta del agente.",
        ) from error

    return ConsultaResponse(
        thread_id=datos.thread_id,
        respuesta=respuesta,
    )


@app.get("/estado/{thread_id}", response_model=EstadoResponse)
def estado(thread_id: str) -> EstadoResponse:
    """
    Devuelve el historial visible asociado a un thread_id.
    """
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