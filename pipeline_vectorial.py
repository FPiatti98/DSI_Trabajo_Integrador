import hashlib
import json
import os
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types


BASE_DIR = Path(__file__).resolve().parent
BASE_PATH = BASE_DIR / "base_conocimiento.json"
INDEX_PATH = BASE_DIR / "indice_faiss.index"
MANIFEST_PATH = BASE_DIR / "documentos_indexados.json"

TOP_K = 3


def cargar_base():
    contenido = BASE_PATH.read_text(encoding="utf-8")
    documentos = json.loads(contenido)

    if len(documentos) < 15:
        raise ValueError("La base de conocimiento debe tener al menos 15 documentos.")

    huella = hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    return documentos, huella


def crear_cliente():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No se encontró GEMINI_API_KEY. Revisá que esté configurada en el archivo .env."
        )

    return genai.Client(api_key=api_key)


def generar_embeddings_documentos(client, documentos):
    textos = [documento["descripcion_semantica"] for documento in documentos]

    respuesta = client.models.embed_content(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=textos,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )

    return np.array(
        [embedding.values for embedding in respuesta.embeddings],
        dtype=np.float32,
    )


def construir_indice(documentos, huella_base):
    print("No existe un índice persistido válido. Generando embeddings...")

    client = crear_cliente()
    embeddings = generar_embeddings_documentos(client, documentos)

    # Normalización para que la distancia L2 refleje cercanía semántica.
    faiss.normalize_L2(embeddings)

    indice = faiss.IndexFlatL2(embeddings.shape[1])
    indice.add(embeddings)

    faiss.write_index(indice, str(INDEX_PATH))

    manifest = {
        "huella_base": huella_base,
        "documentos": documentos,
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Índice creado y guardado en: {INDEX_PATH.name}")
    print(f"Documentos indexados: {indice.ntotal}")

    return indice, documentos


def cargar_o_construir_indice():
    documentos, huella_actual = cargar_base()

    if INDEX_PATH.exists() and MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        if manifest["huella_base"] == huella_actual:
            indice = faiss.read_index(str(INDEX_PATH))
            print("Índice FAISS cargado desde disco. No se generaron embeddings nuevos.")
            return indice, manifest["documentos"]

        print("La base cambió desde la última indexación. Se reconstruirá el índice.")

    return construir_indice(documentos, huella_actual)


def embedding_consulta(client, consulta):
    respuesta = client.models.embed_content(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=consulta,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )

    vector = np.array([respuesta.embeddings[0].values], dtype=np.float32)
    faiss.normalize_L2(vector)

    return vector


def buscar(indice, documentos, consulta, top_k=TOP_K):
    client = crear_cliente()
    vector_consulta = embedding_consulta(client, consulta)

    distancias, posiciones = indice.search(vector_consulta, top_k)

    print("\n" + "=" * 70)
    print(f"CONSULTA: {consulta}")

    for ranking, (distancia, posicion) in enumerate(
        zip(distancias[0], posiciones[0]),
        start=1,
    ):
        documento = documentos[posicion]

        print(f"\n{ranking}. {documento['id']}")
        print(f"   Distancia L2: {distancia:.4f}")
        print(f"   Categoría: {documento['metadatos']['categoria']}")
        print(f"   Descripción: {documento['descripcion_semantica']}")


def main():
    indice, documentos = cargar_o_construir_indice()

    consultas_prueba = [
        "¿Dónde está mi pedido #4587 y cuándo llegará?",
        "Mi notebook no enciende y necesito asistencia técnica.",
        "El producto llegó roto y quiero devolverlo.",
    ]

    for consulta in consultas_prueba:
        buscar(indice, documentos, consulta)


if __name__ == "__main__":
    main()