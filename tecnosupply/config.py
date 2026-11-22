from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

# Conservamos los datos en su ubicación actual durante la reorganización.
DIRECTORIO_DATOS_LOCALES = RAIZ_PROYECTO / "entrega_4"

RUTA_BASE_CONOCIMIENTO = RAIZ_PROYECTO / "base_conocimiento.json"
RUTA_BD_OPERACIONES = DIRECTORIO_DATOS_LOCALES / "operaciones.db"
RUTA_MEMORIA = DIRECTORIO_DATOS_LOCALES / "memoria_agente.sqlite"
RUTA_BD_METRICAS = DIRECTORIO_DATOS_LOCALES / "observabilidad.sqlite"
RUTA_CHROMA_OLLAMA = DIRECTORIO_DATOS_LOCALES / "chroma_ollama"

CARPETA_LOGS = DIRECTORIO_DATOS_LOCALES / "logs"
RUTA_LOG_JSON = CARPETA_LOGS / "agente.jsonl"

URL_OLLAMA = "http://localhost:11434"
MODELO_OLLAMA = "qwen3:4b-instruct"
MODELO_EMBEDDINGS = "nomic-embed-text"
NOMBRE_COLECCION = "conocimiento_tecnosupply_ollama"
LIMITE_ITERACIONES = 8