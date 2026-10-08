import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter


CARPETA_RAIZ = Path(__file__).resolve().parent.parent
RUTA_BASE = CARPETA_RAIZ / "base_conocimiento.json"
RUTA_CHROMA = CARPETA_RAIZ / "chroma_db"

COLECCION_CHUNKS = "conocimiento_tecnosupply_chunks"

TAMANIO_CHUNK = 250
SOLAPAMIENTO = 50


def preparar_metadatos(documento, indice_chunk):
    metadatos = documento["metadatos"]

    tags = metadatos.get("tags_regionales", [])

    if isinstance(tags, list):
        tags = ", ".join(tags)

    return {
        "document_id": documento["id"],
        "chunk_index": indice_chunk,
        "categoria": metadatos["categoria"],
        "vigente": metadatos["vigente"],
        "sucursal": metadatos["sucursal"],
        "tags_regionales": tags,
    }


def main():
    load_dotenv(CARPETA_RAIZ / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY en el archivo .env.")

    documentos = json.loads(
        RUTA_BASE.read_text(encoding="utf-8")
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TAMANIO_CHUNK,
        chunk_overlap=SOLAPAMIENTO,
        length_function=len,
    )

    ids = []
    textos = []
    metadatos = []

    for documento in documentos:
        chunks = splitter.split_text(
            documento["descripcion_semantica"]
        )

        for indice_chunk, chunk in enumerate(chunks):
            ids.append(
                f"{documento['id']}_chunk_{indice_chunk}"
            )
            textos.append(chunk)
            metadatos.append(
                preparar_metadatos(documento, indice_chunk)
            )

    print("Generando embeddings para los chunks...")
    cliente_gemini = genai.Client(api_key=api_key)

    respuesta = cliente_gemini.models.embed_content(
        model=os.getenv(
            "GEMINI_EMBEDDING_MODEL",
            "gemini-embedding-001",
        ),
        contents=textos,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )

    embeddings = [
        embedding.values
        for embedding in respuesta.embeddings
    ]

    cliente_chroma = chromadb.PersistentClient(
        path=str(RUTA_CHROMA)
    )

    coleccion = cliente_chroma.get_or_create_collection(
        name=COLECCION_CHUNKS,
        configuration={
            "hnsw": {
                "space": "cosine",
            }
        },
    )

    coleccion.upsert(
        ids=ids,
        documents=textos,
        metadatas=metadatos,
        embeddings=embeddings,
    )

    print("=== Reindexación con chunking B.2 ===")
    print(f"Documentos originales: {len(documentos)}")
    print(f"Chunk size: {TAMANIO_CHUNK} caracteres")
    print(f"Chunk overlap: {SOLAPAMIENTO} caracteres")
    print(f"Chunks generados: {len(textos)}")
    print(f"Chunks persistidos en ChromaDB: {coleccion.count()}")
    print(f"Colección nueva: {COLECCION_CHUNKS}")


if __name__ == "__main__":
    main()