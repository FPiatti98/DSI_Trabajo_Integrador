import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


CARPETA_RAIZ = Path(__file__).resolve().parent.parent
BASE_PATH = CARPETA_RAIZ / "base_conocimiento.json"

# Precio de entrada de Gemini 2.5 Flash en el nivel pago estándar:
# USD 0.30 por cada 1.000.000 de tokens de entrada.
PRECIO_INPUT_USD_POR_MILLON = 0.30


def contar_tokens(client, modelo, texto):
    respuesta = client.models.count_tokens(
        model=modelo,
        contents=texto,
    )
    return respuesta.total_tokens


def main():
    load_dotenv(CARPETA_RAIZ / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY en el archivo .env.")

    modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    documentos = json.loads(BASE_PATH.read_text(encoding="utf-8"))
    base_completa = BASE_PATH.read_text(encoding="utf-8")

    consulta_ejemplo = (
        "Compré una notebook hace una semana y todavía no recibí mi pedido. "
        "¿Podés decirme cuándo llegará? Mi número de pedido es #4587."
    )

    prompt_estatico = f"""
Sos el asistente de atención al cliente de TecnoSupply Argentina.
Usá exclusivamente la siguiente base de conocimiento para responder.

BASE DE CONOCIMIENTO COMPLETA:
{base_completa}

CONSULTA DEL CLIENTE:
{consulta_ejemplo}
"""

    client = genai.Client(api_key=api_key)

    tokens_base = contar_tokens(client, modelo, base_completa)
    tokens_prompt = contar_tokens(client, modelo, prompt_estatico)

    costo_por_consulta = (
        tokens_prompt / 1_000_000
    ) * PRECIO_INPUT_USD_POR_MILLON

    costo_por_1000_consultas = costo_por_consulta * 1000

    print("=== Medición de contexto estático — A.1 ===")
    print(f"Modelo: {modelo}")
    print(f"Documentos en la base: {len(documentos)}")
    print(f"Tokens de la base completa: {tokens_base}")
    print(f"Tokens del prompt estático completo: {tokens_prompt}")
    print(f"Costo estimado por consulta: USD {costo_por_consulta:.6f}")
    print(f"Costo estimado por 1.000 consultas: USD {costo_por_1000_consultas:.4f}")


if __name__ == "__main__":
    main()