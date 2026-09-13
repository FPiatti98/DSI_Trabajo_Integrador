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


def generar_embedding_consulta(consulta):
    load_dotenv(CARPETA_RAIZ / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY en el archivo .env.")

    cliente_gemini = genai.Client(api_key=api_key)

    respuesta = cliente_gemini.models.embed_content(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=consulta,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )

    return respuesta.embeddings[0].values


def construir_where(categoria, sucursal, solo_activos):
    condiciones = []

    if categoria:
        condiciones.append(
            {"categoria": {"$eq": categoria}}
        )

    if sucursal:
        condiciones.append(
            {"sucursal": {"$eq": sucursal}}
        )

    if solo_activos:
        condiciones.append(
            {"vigente": {"$eq": True}}
        )

    if not condiciones:
        return None

    if len(condiciones) == 1:
        return condiciones[0]

    return {"$and": condiciones}


def buscar_tecnosupply(
    query_semantica,
    categoria=None,
    sucursal=None,
    solo_activos=True,
    n_resultados=3,
):
    cliente_chroma = chromadb.PersistentClient(path=str(RUTA_CHROMA))

    coleccion = cliente_chroma.get_collection(
        name=NOMBRE_COLECCION,
    )

    where = construir_where(
        categoria=categoria,
        sucursal=sucursal,
        solo_activos=solo_activos,
    )

    embedding_consulta = generar_embedding_consulta(query_semantica)

    resultado = coleccion.query(
        query_embeddings=[embedding_consulta],
        where=where,
        n_results=n_resultados,
        include=["documents", "metadatas", "distances"],
    )

    return resultado, where


def mostrar_resultados(resultado):
    ids = resultado["ids"][0]
    documentos = resultado["documents"][0]
    metadatos = resultado["metadatas"][0]
    distancias = resultado["distances"][0]

    if not ids:
        print("\nNo se encontraron documentos que cumplan el filtro.")
        return

    print("\nResultados encontrados:")

    for posicion, (doc_id, documento, metadata, distancia) in enumerate(
        zip(ids, documentos, metadatos, distancias),
        start=1,
    ):
        print(f"\n{posicion}. {doc_id}")
        print(f"   Distancia coseno: {distancia:.4f}")
        print(
            "   Metadatos: "
            f"{json.dumps(metadata, ensure_ascii=False)}"
        )
        print(f"   Documento: {documento}")


def main():
    print("=== Búsqueda híbrida — TecnoSupply Argentina ===")

    consulta = input("\nConsulta semántica: ").strip()

    categoria = input(
        "Categoría opcional "
        "(pedidos, soporte, reclamos, facturacion, etc.): "
    ).strip() or None

    sucursal = input(
        "Sucursal opcional (todas o CABA): "
    ).strip() or None

    solo_activos = input(
        "¿Buscar solo documentos vigentes? [S/n]: "
    ).strip().lower() != "n"

    cantidad = input(
        "Cantidad de resultados [3]: "
    ).strip()

    n_resultados = int(cantidad) if cantidad else 3

    resultado, where = buscar_tecnosupply(
        query_semantica=consulta,
        categoria=categoria,
        sucursal=sucursal,
        solo_activos=solo_activos,
        n_resultados=n_resultados,
    )

    print(f"\nFiltro aplicado dentro de ChromaDB: {where}")
    mostrar_resultados(resultado)


if __name__ == "__main__":
    main()