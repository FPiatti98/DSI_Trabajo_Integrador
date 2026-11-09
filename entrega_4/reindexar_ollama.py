from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from langchain_ollama import OllamaEmbeddings

CARPETA_ENTREGA_4 = Path(__file__).resolve().parent
RAIZ_PROYECTO = CARPETA_ENTREGA_4.parent

RUTA_BASE_CONOCIMIENTO = RAIZ_PROYECTO / "base_conocimiento.json"
RUTA_CHROMA_OLLAMA = CARPETA_ENTREGA_4 / "chroma_ollama"
NOMBRE_COLECCION = "conocimiento_tecnosupply_ollama"

MODELO_EMBEDDINGS = "nomic-embed-text"
URL_OLLAMA = "http://localhost:11434"
TAMANIO_LOTE = 10


def normalizar_metadatos(metadatos: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """
    Convierte metadatos al formato permitido por ChromaDB.

    ChromaDB admite textos, números y booleanos. Las listas se convierten a
    texto separado por comas, por ejemplo para conservar tags regionales.
    """
    resultado: dict[str, str | int | float | bool] = {}

    for clave, valor in metadatos.items():
        if valor is None:
            continue

        if isinstance(valor, list):
            resultado[clave] = ", ".join(str(item) for item in valor)
        elif isinstance(valor, (str, int, float, bool)):
            resultado[clave] = valor
        else:
            resultado[clave] = str(valor)

    return resultado


def obtener_registros(ruta: Path) -> list[dict[str, Any]]:
    """Carga la lista de documentos desde base_conocimiento.json."""
    with ruta.open("r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    if isinstance(datos, list):
        return datos

    if isinstance(datos, dict):
        for clave in ("documentos", "base_conocimiento", "datos"):
            if isinstance(datos.get(clave), list):
                return datos[clave]

    raise ValueError(
        "No se encontró una lista de documentos en base_conocimiento.json."
    )


def extraer_texto(registro: dict[str, Any]) -> str:
    """Obtiene el texto del documento aunque la fuente use nombres distintos."""
    for clave in (
    "descripcion_semantica",
    "contenido",
    "documento",
    "texto",
    "text",
    "page_content",
):
        valor = registro.get(clave)

        if isinstance(valor, str) and valor.strip():
            return valor.strip()

    raise ValueError(
        f"El documento {registro.get('id', 'sin ID')} no tiene contenido textual."
    )


def preparar_documentos(
    registros: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[dict[str, str | int | float | bool]]]:
    """Extrae IDs, textos y metadatos de los registros de la base."""
    ids: list[str] = []
    textos: list[str] = []
    metadatos_finales: list[dict[str, str | int | float | bool]] = []

    for indice, registro in enumerate(registros, start=1):
        identificador = str(
            registro.get("id")
            or registro.get("doc_id")
            or registro.get("identificador")
            or f"DOC-SIN-ID-{indice:03d}"
        )

        texto = extraer_texto(registro)

        metadatos = registro.get("metadatos", {})
        if not isinstance(metadatos, dict):
            metadatos = {}

        # También conserva campos que estén en el nivel principal del JSON.
        for clave in ("categoria", "sucursal", "vigente", "tags_regionales"):
            if clave in registro and clave not in metadatos:
                metadatos[clave] = registro[clave]

        metadatos["id"] = identificador

        ids.append(identificador)
        textos.append(texto)
        metadatos_finales.append(normalizar_metadatos(metadatos))

    return ids, textos, metadatos_finales


def main() -> None:
    """Genera una colección Chroma persistente con embeddings locales Ollama."""
    if not RUTA_BASE_CONOCIMIENTO.exists():
        raise FileNotFoundError(
            f"No se encontró la base de conocimiento: {RUTA_BASE_CONOCIMIENTO}"
        )

    registros = obtener_registros(RUTA_BASE_CONOCIMIENTO)
    ids, textos, metadatos = preparar_documentos(registros)

    print("=== Reindexación local con Ollama ===")
    print(f"Modelo de embeddings: {MODELO_EMBEDDINGS}")
    print(f"Documentos de origen: {len(ids)}")
    print("Generando embeddings locales...")

    embeddings = OllamaEmbeddings(
        model=MODELO_EMBEDDINGS,
        base_url=URL_OLLAMA,
    )

    cliente = chromadb.PersistentClient(path=str(RUTA_CHROMA_OLLAMA))

    coleccion = cliente.get_or_create_collection(
        name=NOMBRE_COLECCION,
        metadata={"hnsw:space": "cosine"},
    )

    for inicio in range(0, len(ids), TAMANIO_LOTE):
        fin = inicio + TAMANIO_LOTE
        lote_ids = ids[inicio:fin]
        lote_textos = textos[inicio:fin]
        lote_metadatos = metadatos[inicio:fin]

        lote_embeddings = embeddings.embed_documents(lote_textos)

        coleccion.upsert(
            ids=lote_ids,
            documents=lote_textos,
            metadatas=lote_metadatos,
            embeddings=lote_embeddings,
        )

        print(f"Lote indexado: documentos {inicio + 1} a {min(fin, len(ids))}")

    print("\nReindexación finalizada.")
    print(f"Ruta persistente: {RUTA_CHROMA_OLLAMA}")
    print(f"Colección: {NOMBRE_COLECCION}")
    print(f"Documentos almacenados: {coleccion.count()}")


if __name__ == "__main__":
    main()