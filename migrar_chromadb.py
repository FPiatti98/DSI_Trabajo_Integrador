from pathlib import Path

import chromadb

from pipeline_vectorial import (
    cargar_base,
    crear_cliente,
    generar_embeddings_documentos,
)


CARPETA_RAIZ = Path(__file__).resolve().parent
RUTA_CHROMA = CARPETA_RAIZ / "chroma_db"
NOMBRE_COLECCION = "conocimiento_tecnosupply"


def preparar_metadatos(documento):
    metadatos = documento["metadatos"]

    # ChromaDB admite valores simples como texto, número o booleano.
    # Por eso los tags se conservan en un único texto.
    return {
        "categoria": metadatos["categoria"],
        "vigente": metadatos["vigente"],
        "sucursal": metadatos["sucursal"],
        "tags_regionales": ", ".join(metadatos["tags_regionales"]),
    }


def main():
    documentos, _ = cargar_base()

    print("Generando embeddings de la base de conocimiento...")
    cliente_gemini = crear_cliente()
    embeddings = generar_embeddings_documentos(cliente_gemini, documentos)

    print("Conectando con ChromaDB persistente...")
    cliente_chroma = chromadb.PersistentClient(path=str(RUTA_CHROMA))

    coleccion = cliente_chroma.get_or_create_collection(
        name=NOMBRE_COLECCION,
        metadata={"hnsw:space": "cosine"},
    )

    coleccion.upsert(
        ids=[documento["id"] for documento in documentos],
        documents=[
            documento["descripcion_semantica"]
            for documento in documentos
        ],
        metadatas=[
            preparar_metadatos(documento)
            for documento in documentos
        ],
        embeddings=embeddings.tolist(),
    )

    print("Migración finalizada.")
    print(f"Ruta persistente: {RUTA_CHROMA}")
    print(f"Colección: {NOMBRE_COLECCION}")
    print(f"Documentos almacenados: {coleccion.count()}")
    print("Se utilizó upsert: al reejecutar no se duplican documentos.")


if __name__ == "__main__":
    main()