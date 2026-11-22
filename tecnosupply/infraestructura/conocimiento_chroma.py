from typing import Any

import chromadb
from langchain_ollama import OllamaEmbeddings

from tecnosupply.config import (
    MODELO_EMBEDDINGS,
    NOMBRE_COLECCION,
    RUTA_CHROMA_OLLAMA,
    URL_OLLAMA,
)


def buscar_documentos(
    consulta: str,
    n_resultados: int = 3,
    filtros: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Recupera documentos mediante embeddings locales y ChromaDB.

    Recibe los filtros decididos por la aplicación.
    Devuelve datos recuperados, sin redactar una respuesta al usuario.
    """
    if not RUTA_CHROMA_OLLAMA.exists():
        raise FileNotFoundError(
            "No existe la base vectorial local. "
            "Ejecutá primero el script de reindexación."
        )

    cliente = chromadb.PersistentClient(
        path=str(RUTA_CHROMA_OLLAMA)
    )
    coleccion = cliente.get_collection(
        name=NOMBRE_COLECCION
    )

    embeddings = OllamaEmbeddings(
        model=MODELO_EMBEDDINGS,
        base_url=URL_OLLAMA,
    )
    vector_consulta = embeddings.embed_query(consulta)

    resultado = coleccion.query(
        query_embeddings=[vector_consulta],
        n_results=n_resultados,
        where=filtros,
        include=["documents", "metadatas", "distances"],
    )

    documentos = []

    for identificador, texto, metadatos, distancia in zip(
        resultado["ids"][0],
        resultado["documents"][0],
        resultado["metadatas"][0],
        resultado["distances"][0],
    ):
        metadatos = metadatos or {}

        documentos.append(
            {
                "id": identificador,
                "categoria": metadatos.get("categoria", "N/D"),
                "sucursal": metadatos.get("sucursal", "N/D"),
                "vigente": metadatos.get("vigente", "N/D"),
                "distancia": round(float(distancia), 4),
                "contenido": texto,
            }
        )

    return documentos