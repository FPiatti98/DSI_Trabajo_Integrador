from langchain_ollama import ChatOllama

from tecnosupply.config import MODELO_OLLAMA, URL_OLLAMA


def crear_modelo() -> ChatOllama:
    """Construye la conexión con el modelo local del agente."""
    return ChatOllama(
        model=MODELO_OLLAMA,
        base_url=URL_OLLAMA,
        temperature=0,
    )