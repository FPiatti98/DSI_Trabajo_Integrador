"""Contratos de datos del sistema de clasificación de emails."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


Intencion = Literal[
    "CONSULTA_PEDIDO",
    "RECLAMO",
    "FACTURACION",
    "SOPORTE",
    "CONSULTA_GENERAL",
]

Prioridad = Literal["BAJA", "MEDIA", "ALTA"]


class ClasificacionEmail(BaseModel):
    """Salida estructurada generada por el LLM para un email recibido."""

    model_config = ConfigDict(str_strip_whitespace=True)

    intencion: Intencion
    prioridad: Prioridad
    numero_pedido: str | None = None
    producto: str | None = None
    detalle: str | None = None

    @field_validator("numero_pedido", mode="before")
    @classmethod
    def limpiar_y_validar_numero_pedido(cls, valor: object) -> str | None:
        """Normaliza '#4587' a '4587' y rechaza identificadores no numéricos."""
        if valor is None:
            return None

        numero = str(valor).strip().lstrip("#").strip()
        if not numero:
            return None
        if not numero.isdigit():
            raise ValueError("numero_pedido debe contener únicamente dígitos")
        if len(numero) > 50:
            raise ValueError("numero_pedido no puede superar los 50 dígitos")

        return numero
