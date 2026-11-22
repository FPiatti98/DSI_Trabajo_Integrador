from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from tecnosupply.config import MODELO_OLLAMA, RAIZ_PROYECTO

# La trazabilidad debe configurarse antes de importar el agente.
# Se conservan el proyecto y las opciones de la API anterior.
load_dotenv(RAIZ_PROYECTO / ".env", override=True)

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "tecnosupply-agente-entrega4"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "tecnosupply-agente-entrega4"

if os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

from tecnosupply.infraestructura.observabilidad import (
    inicializar_observabilidad,
    registrar_log_json,
)
from tecnosupply.presentacion.api import router

app = FastAPI(
    title="API del Agente TecnoSupply",
    description=(
        "API REST para consultar un agente ReAct con herramientas, memoria "
        "SQLite, recuperación RAG local, observabilidad y guardrails."
    ),
    version="1.0.0",
)


@app.on_event("startup")
def iniciar_api() -> None:
    """Inicializa los recursos de observabilidad al iniciar la API."""
    inicializar_observabilidad()
    registrar_log_json(
        "api_iniciada",
        modelo=MODELO_OLLAMA,
        proyecto_langsmith=os.environ["LANGSMITH_PROJECT"],
    )


app.include_router(router)
