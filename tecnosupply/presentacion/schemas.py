from pydantic import BaseModel, Field


class ConsultaRequest(BaseModel):
    """Datos que debe enviar el cliente para consultar al agente."""

    consulta: str = Field(
        ...,
        min_length=1,
        description="Consulta del usuario en lenguaje natural.",
    )

    thread_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Identificador persistente de la conversación.",
    )


class ConsultaResponse(BaseModel):
    """Respuesta pública del endpoint de consultas."""

    thread_id: str
    respuesta: str
    herramientas_usadas: list[str]


class EstadoResponse(BaseModel):
    """Historial público de una conversación."""

    thread_id: str
    cantidad_mensajes: int
    historial: list[dict[str, str]]