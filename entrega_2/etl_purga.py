import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types


CARPETA_RAIZ = Path(__file__).resolve().parent
ARCHIVO_ENTRADA = CARPETA_RAIZ / "base_conocimiento_sucia.json"
ARCHIVO_SALIDA = CARPETA_RAIZ / "base_conocimiento_limpia.json"
ARCHIVO_LOG = CARPETA_RAIZ / "log_etl_purga.md"

# Solo se considera casi-duplicado si la distancia coseno es menor a 0.08.
UMBRAL_DISTANCIA_COSENO = 0.08


def normalizar_booleano(valor):
    if isinstance(valor, bool):
        return valor

    if isinstance(valor, str):
        return valor.strip().lower() in {
            "true",
            "1",
            "si",
            "sí",
            "activo",
            "vigente",
        }

    return bool(valor)


def normalizar_tags(valor):
    if isinstance(valor, list):
        return [str(tag).strip() for tag in valor if str(tag).strip()]

    if isinstance(valor, str):
        return [
            tag.strip()
            for tag in valor.split(",")
            if tag.strip()
        ]

    return []


def obtener_primer_valor(diccionario, claves, valor_por_defecto):
    for clave in claves:
        if clave in diccionario:
            return diccionario[clave]

    return valor_por_defecto


def normalizar_documento(documento):
    metadatos_originales = documento.get("metadatos", {})

    categoria = obtener_primer_valor(
        metadatos_originales,
        ["categoria", "categoria_producto", "categoriaProducto", "category"],
        "sin_categoria",
    )

    vigente = obtener_primer_valor(
        metadatos_originales,
        ["vigente", "estaVigente", "activo"],
        True,
    )

    tags = obtener_primer_valor(
        metadatos_originales,
        ["tags_regionales", "tagsRegionales", "tagsRegional"],
        [],
    )

    sucursal = metadatos_originales.get("sucursal", "todas")

    return {
        "id": str(documento["id"]).strip(),
        "descripcion_semantica": str(
            documento["descripcion_semantica"]
        ).strip(),
        "metadatos": {
            "categoria": str(categoria).strip().lower(),
            "vigente": normalizar_booleano(vigente),
            "sucursal": str(sucursal).strip().lower(),
            "tags_regionales": normalizar_tags(tags),
        },
    }


def resolver_colisiones_ids(documentos):
    ids_usados = {}
    documentos_resueltos = []
    log_colisiones = []

    for documento in documentos:
        documento_normalizado = normalizar_documento(documento)
        id_original = documento_normalizado["id"]

        if id_original not in ids_usados:
            ids_usados[id_original] = 0
        else:
            ids_usados[id_original] += 1
            id_nuevo = f"{id_original}-ETL-{ids_usados[id_original]:02d}"

            log_colisiones.append(
                f"- Colisión resuelta: `{id_original}` pasó a llamarse `{id_nuevo}`."
            )

            documento_normalizado["id"] = id_nuevo

        documentos_resueltos.append(documento_normalizado)

    return documentos_resueltos, log_colisiones


def generar_embeddings(client, documentos):
    textos = [
        documento["descripcion_semantica"]
        for documento in documentos
    ]

    respuesta = client.models.embed_content(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=textos,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=768,
        ),
    )

    embeddings = np.array(
        [embedding.values for embedding in respuesta.embeddings],
        dtype=np.float32,
    )

    normas = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / normas


def purgar_casi_duplicados(documentos, embeddings):
    eliminados = set()
    log_purga = []

    for indice_a in range(len(documentos)):
        if indice_a in eliminados:
            continue

        for indice_b in range(indice_a + 1, len(documentos)):
            if indice_b in eliminados:
                continue

            # Se compara solamente dentro de la misma categoría.
            categoria_a = documentos[indice_a]["metadatos"]["categoria"]
            categoria_b = documentos[indice_b]["metadatos"]["categoria"]

            if categoria_a != categoria_b:
                continue

            similitud = float(
                np.dot(embeddings[indice_a], embeddings[indice_b])
            )
            distancia_coseno = 1 - similitud

            if distancia_coseno < UMBRAL_DISTANCIA_COSENO:
                eliminados.add(indice_b)

                log_purga.append(
                    f"- Se eliminó `{documentos[indice_b]['id']}` "
                    f"por ser casi-duplicado de `{documentos[indice_a]['id']}` "
                    f"en la categoría `{categoria_a}` "
                    f"(distancia coseno: `{distancia_coseno:.4f}`)."
                )

    documentos_limpios = [
        documento
        for indice, documento in enumerate(documentos)
        if indice not in eliminados
    ]

    return documentos_limpios, log_purga


def guardar_log(colisiones, purga, cantidad_inicial, cantidad_final):
    contenido = [
        "# Log de ETL y purga semántica",
        "",
        f"- Documentos iniciales: {cantidad_inicial}",
        f"- Documentos finales: {cantidad_final}",
        f"- Umbral de distancia coseno: {UMBRAL_DISTANCIA_COSENO}",
        "- Comparación semántica limitada a documentos de la misma categoría.",
        "",
        "## Colisiones de IDs resueltas",
        *(colisiones or ["- No se detectaron colisiones de IDs."]),
        "",
        "## Documentos eliminados por purga semántica",
        *(purga or ["- No se detectaron casi-duplicados."]),
    ]

    ARCHIVO_LOG.write_text(
        "\n".join(contenido),
        encoding="utf-8",
    )


def main():
    load_dotenv(CARPETA_RAIZ / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY en el archivo .env.")

    documentos_originales = json.loads(
        ARCHIVO_ENTRADA.read_text(encoding="utf-8")
    )

    documentos_normalizados, colisiones = resolver_colisiones_ids(
        documentos_originales
    )

    print("Generando embeddings para detectar casi-duplicados...")
    client = genai.Client(api_key=api_key)
    embeddings = generar_embeddings(client, documentos_normalizados)

    documentos_limpios, purga = purgar_casi_duplicados(
        documentos_normalizados,
        embeddings,
    )

    ARCHIVO_SALIDA.write_text(
        json.dumps(documentos_limpios, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    guardar_log(
        colisiones=colisiones,
        purga=purga,
        cantidad_inicial=len(documentos_originales),
        cantidad_final=len(documentos_limpios),
    )

    print("ETL finalizado.")
    print(f"Documentos iniciales: {len(documentos_originales)}")
    print(f"Documentos finales: {len(documentos_limpios)}")
    print(f"Base limpia generada: {ARCHIVO_SALIDA.name}")
    print(f"Log generado: {ARCHIVO_LOG.name}")


if __name__ == "__main__":
    main()