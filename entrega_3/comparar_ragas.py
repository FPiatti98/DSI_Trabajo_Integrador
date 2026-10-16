import json
from pathlib import Path

CARPETA_ENTREGA = Path(__file__).resolve().parent

ARCHIVO_BASICO = CARPETA_ENTREGA / "resultados_ragas_basico.json"
ARCHIVO_AVANZADO = CARPETA_ENTREGA / "resultados_ragas_avanzado.json"
ARCHIVO_SALIDA = CARPETA_ENTREGA / "comparacion_ragas.json"

METRICAS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]


def cargar_resultados(ruta: Path):
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta.name}. "
            "Primero ejecutá la evaluación correspondiente."
        )

    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def main():
    basico = cargar_resultados(ARCHIVO_BASICO)
    avanzado = cargar_resultados(ARCHIVO_AVANZADO)

    promedios_basico = basico["promedios"]
    promedios_avanzado = avanzado["promedios"]

    comparacion = {
        "cantidad_consultas": basico["cantidad_consultas"],
        "metricas": {},
    }

    print("=== Comparación RAGAS: básico vs. avanzado ===\n")
    print(
        f"{'Métrica':<22} {'Básico':>10} {'Avanzado':>10} {'Delta':>10}"
    )
    print("-" * 58)

    for metrica in METRICAS:
        valor_basico = float(promedios_basico[metrica])
        valor_avanzado = float(promedios_avanzado[metrica])
        delta = valor_avanzado - valor_basico

        comparacion["metricas"][metrica] = {
            "basico": round(valor_basico, 4),
            "avanzado": round(valor_avanzado, 4),
            "delta": round(delta, 4),
        }

        print(
            f"{metrica:<22} "
            f"{valor_basico:>10.4f} "
            f"{valor_avanzado:>10.4f} "
            f"{delta:>+10.4f}"
        )

    with ARCHIVO_SALIDA.open("w", encoding="utf-8") as archivo:
        json.dump(comparacion, archivo, ensure_ascii=False, indent=2)

    print(f"\nComparación guardada en: {ARCHIVO_SALIDA.name}")


if __name__ == "__main__":
    main()