import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types


CARPETA_RAIZ = Path(__file__).resolve().parent
RUTA_CHROMA = CARPETA_RAIZ / "chroma_db"
NOMBRE_COLECCION = "conocimiento_tecnosupply"
ID_DOCUMENTO = "DOC-011"


def main():
    load_dotenv(CARPETA_RAIZ / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY en el archivo .env.")

    nueva_descripcion = (
        "Actualización operativa de stock: la notebook Lenovo ThinkPad E14 "
        "se encuentra temporalmente sin disponibilidad para entrega inmediata "
        "en TecnoSupply Argentina. El próximo ingreso estimado de unidades es "
        "durante la próxima semana. Atención al Cliente debe evitar confirmar "
        "una venta hasta que el sistema de inventario informe stock disponible."
    )

    nuevos_metadatos = {
        "categoria": "stock",
        "vigente": True,
        "sucursal": "todas",
        "tags_regionales": "stock, disponibilidad, notebook, ingreso de mercadería",
    }

    cliente_gemini = genai.Client(api_key=api_key)

    respuesta = cliente_gemini.models.embed_content(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=nueva_descripcion,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )

    embedding = respuesta.embeddings[0].values

    cliente_chroma = chromadb.PersistentClient(path=str(RUTA_CHROMA))
    coleccion = cliente_chroma.get_collection(name=NOMBRE_COLECCION)

    coleccion.upsert(
        ids=[ID_DOCUMENTO],
        documents=[nueva_descripcion],
        metadatas=[nuevos_metadatos],
        embeddings=[embedding],
    )

    verificacion = coleccion.get(
        ids=[ID_DOCUMENTO],
        include=["documents", "metadatas"],
    )

    print("Evento de negocio aplicado correctamente:\n")
    print(json.dumps(verificacion, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()