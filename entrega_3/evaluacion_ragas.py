import argparse
import json
import math
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from ragas.run_config import RunConfig

from rag_avanzado_ollama import crear_cadena_rag_avanzada
from rag_pipeline import crear_cadena_rag

CARPETA_ENTREGA = Path(__file__).resolve().parent
ARCHIVO_DATASET = CARPETA_ENTREGA / "dataset_dorado.json"

MODELO_OLLAMA = "qwen2.5:3b"
MODELO_EMBEDDINGS_OLLAMA = "nomic-embed-text"
URL_OLLAMA = "http://localhost:11434"

METRICAS = {
    "faithfulness": faithfulness,
    "answer_relevancy": answer_relevancy,
    "context_precision": context_precision,
    "context_recall": context_recall,
}


def cargar_json(ruta: Path, valor_por_defecto):
    if not ruta.exists():
        return valor_por_defecto

    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)

    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"El archivo {ruta.name} está vacío o contiene JSON inválido."
        ) from error


def guardar_json(ruta: Path, contenido):
    ruta_temporal = ruta.with_suffix(f"{ruta.suffix}.tmp")

    with ruta_temporal.open("w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)

    ruta_temporal.replace(ruta)


def cargar_dataset_dorado():
    return cargar_json(ARCHIVO_DATASET, [])


def ruta_cache(modo: str):
    return CARPETA_ENTREGA / f"cache_respuestas_{modo}.json"


def ruta_resultados(modo: str):
    return CARPETA_ENTREGA / f"resultados_ragas_{modo}.json"


def crear_pipeline(modo: str):
    if modo == "basico":
        cadena = crear_cadena_rag(k=3)

        def ejecutar(pregunta: str):
            resultado = cadena.invoke({"pregunta": pregunta})

            return {
                "respuesta": resultado["respuesta"],
                "documentos": resultado["documentos"],
            }

        return ejecutar

    cadena = crear_cadena_rag_avanzada(
        k_recuperacion=12,
        cantidad_final=4,
    )

    def ejecutar(pregunta: str):
        resultado = cadena(pregunta)

        return {
            "respuesta": resultado["respuesta"],
            "documentos": resultado["documentos"],
        }

    return ejecutar


def preparar_datos_ragas(casos, modo: str):
    cache = cargar_json(ruta_cache(modo), {})
    faltantes = [caso["id"] for caso in casos if caso["id"] not in cache]

    if faltantes:
        print(f"Faltan respuestas en caché: {faltantes}")
        print("Se generarán mediante el pipeline RAG correspondiente.")

        pipeline = crear_pipeline(modo)

        for caso in casos:
            identificador = caso["id"]

            if identificador in cache:
                continue

            print(f"Generando respuesta para {identificador}...")

            resultado = pipeline(caso["pregunta"])

            cache[identificador] = {
                "pregunta": caso["pregunta"],
                "respuesta": resultado["respuesta"],
                "contextos": [
                    documento.page_content
                    for documento in resultado["documentos"]
                ],
            }

            guardar_json(ruta_cache(modo), cache)

    preguntas = []
    respuestas = []
    contextos = []
    referencias = []

    for caso in casos:
        guardado = cache[caso["id"]]

        preguntas.append(caso["pregunta"])
        respuestas.append(guardado["respuesta"])
        contextos.append(guardado["contextos"])
        referencias.append(caso["respuesta_referencia"])

    return Dataset.from_dict(
        {
            "question": preguntas,
            "answer": respuestas,
            "contexts": contextos,
            "ground_truth": referencias,
        }
    )


def crear_estado_resultados(casos, modo: str):
    ruta = ruta_resultados(modo)
    estado = cargar_json(ruta, None)

    if estado is not None:
        return estado

    return {
        "modo": modo,
        "evaluador": f"Ollama local ({MODELO_OLLAMA})",
        "cantidad_consultas": len(casos),
        "promedios": {},
        "detalle_promedios": {},
        "resultados_por_consulta": [
            {
                "id": caso["id"],
                "pregunta": caso["pregunta"],
                "tipo": caso["tipo"],
                "metricas": {},
            }
            for caso in casos
        ],
    }


def crear_evaluadores():
    # Ollama se ejecuta localmente: no requiere API key ni cuota externa.
    llm_evaluador = ChatOllama(
        model=MODELO_OLLAMA,
        base_url=URL_OLLAMA,
        temperature=0,
        num_ctx=8192,
    )

    embeddings_evaluador = OllamaEmbeddings(
        model=MODELO_EMBEDDINGS_OLLAMA,
        base_url=URL_OLLAMA,
    )

    return (
        LangchainLLMWrapper(llm_evaluador),
        LangchainEmbeddingsWrapper(embeddings_evaluador),
    )


def obtener_metrica(nombre_metrica: str):
    metrica = METRICAS[nombre_metrica]

    # Una sola generación por caso para mantener la evaluación ágil.
    if nombre_metrica == "answer_relevancy":
        metrica.strictness = 1

    return metrica


def actualizar_promedios(estado, cantidad_casos: int):
    estado["promedios"] = {}
    estado["detalle_promedios"] = {}

    for nombre_metrica in METRICAS:
        valores_brutos = [
            fila["metricas"][nombre_metrica]
            for fila in estado["resultados_por_consulta"]
            if nombre_metrica in fila["metricas"]
        ]

        valores_validos = [
            valor
            for valor in valores_brutos
            if isinstance(valor, (int, float)) and math.isfinite(valor)
        ]

        cantidad_nan = len(valores_brutos) - len(valores_validos)

        if len(valores_brutos) == cantidad_casos and valores_validos:
            estado["promedios"][nombre_metrica] = round(
                sum(valores_validos) / len(valores_validos),
                4,
            )

        estado["detalle_promedios"][nombre_metrica] = {
            "casos_evaluados": len(valores_brutos),
            "casos_validos": len(valores_validos),
            "casos_nan_excluidos": cantidad_nan,
            "total_casos": cantidad_casos,
        }
def evaluar_metrica(
    dataset_ragas,
    casos,
    modo: str,
    nombre_metrica: str,
    llm_evaluador,
    embeddings_evaluador,
):
    estado = crear_estado_resultados(casos, modo)
    ruta = ruta_resultados(modo)
    metrica = obtener_metrica(nombre_metrica)

    print(f"\n=== Evaluando métrica: {nombre_metrica} ===")
    print(f"Evaluador local: {MODELO_OLLAMA}")

    for indice, caso in enumerate(casos):
        fila_guardada = estado["resultados_por_consulta"][indice]

        if nombre_metrica in fila_guardada["metricas"]:
            puntaje = fila_guardada["metricas"][nombre_metrica]

            print(
                f"[{indice + 1}/{len(casos)}] {caso['id']} "
                f"ya evaluado: {puntaje}"
            )
            continue

        print(
            f"[{indice + 1}/{len(casos)}] "
            f"Evaluando {caso['id']} - {caso['tipo']}..."
        )

        fila_dataset = dataset_ragas[indice]

        dataset_individual = Dataset.from_dict(
            {
                columna: [fila_dataset[columna]]
                for columna in dataset_ragas.column_names
            }
        )

        resultado = evaluate(
            dataset=dataset_individual,
            metrics=[metrica],
            llm=llm_evaluador,
            embeddings=embeddings_evaluador,
            run_config=RunConfig(
                max_workers=1,
                timeout=300,
                max_retries=1,
            ),
        )

        dataframe = resultado.to_pandas()
        puntaje = float(dataframe[nombre_metrica].iloc[0])

        fila_guardada["metricas"][nombre_metrica] = round(puntaje, 4)

        actualizar_promedios(estado, len(casos))
        guardar_json(ruta, estado)

        print(f"   Puntaje guardado: {puntaje:.4f}")

    actualizar_promedios(estado, len(casos))
    guardar_json(ruta, estado)

    print(f"\nResultados guardados en: {ruta.name}")

    if nombre_metrica in estado["promedios"]:
        print(
            f"Promedio {nombre_metrica}: "
            f"{estado['promedios'][nombre_metrica]:.4f}"
        )
    else:
        detalle = estado["detalle_promedios"][nombre_metrica]

        print(
            f"Métrica incompleta o con valores NaN. "
            f"Casos válidos: {detalle['casos_validos']}/"
            f"{detalle['total_casos']}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Evalúa el RAG mediante RAGAS con Ollama local."
    )

    parser.add_argument(
        "--modo",
        choices=["basico", "avanzado"],
        default="basico",
    )

    parser.add_argument(
        "--metrica",
        choices=list(METRICAS.keys()),
        required=True,
    )

    argumentos = parser.parse_args()

    load_dotenv()

    casos = cargar_dataset_dorado()
    dataset_ragas = preparar_datos_ragas(casos, argumentos.modo)

    llm_evaluador, embeddings_evaluador = crear_evaluadores()

    evaluar_metrica(
        dataset_ragas=dataset_ragas,
        casos=casos,
        modo=argumentos.modo,
        nombre_metrica=argumentos.metrica,
        llm_evaluador=llm_evaluador,
        embeddings_evaluador=embeddings_evaluador,
    )


if __name__ == "__main__":
    main()