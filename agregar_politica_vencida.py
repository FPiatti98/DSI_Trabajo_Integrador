import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types


CARPETA_RAIZ = Path(__file__).resolve().parent
RUTA_CHROMA = CARPETA_RAIZ / "chroma_db"
NOMBRE_COLECCION = "conocimiento_tecnosupply"


def main():
    load_dotenv(CARPETA_RAIZ / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY en el archivo .env.")

    descripcion = (
        "Política histórica archivada, no vigente: anteriormente TecnoSupply "
        "Argentina informaba entrega express garantizada dentro de 24 horas "
        "para notebooks con stock. Esta condición dejó de aplicarse y no debe "
        "utilizarse para responder consultas actuales de clientes."
    )

    metadatos = {
        "categoria": "envios",
        "vigente": False,
        "sucursal": "todas",
        "tags_regionales": (
            "politica archivada, entrega express, 24 horas, "
            "no vigente, notebook"
        ),
    }

    cliente_gemini = genai.Client(api_key=api_key)

    respuesta = cliente_gemini.models.embed_content(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=descripcion,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )

    cliente_chroma = chromadb.PersistentClient(path=str(RUTA_CHROMA))
    coleccion = cliente_chroma.get_collection(name=NOMBRE_COLECCION)

    coleccion.upsert(
        ids=["DOC-019"],
        documents=[descripcion],
        metadatas=[metadatos],
        embeddings=[respuesta.embeddings[0].values],
    )

    print("Política histórica cargada correctamente.")
    print("ID: DOC-019")
    print("Vigente: False")


if __name__ == "__main__":
    main()