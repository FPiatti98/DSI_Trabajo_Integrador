# Entrega 2 — Recuperación vectorial y ETL

Este directorio conserva el código, los datos de limpieza, los resultados y las evidencias de la segunda entrega. La aplicación final por capas está en `tecnosupply/`; se ejecuta siguiendo el README de la raíz.

## Organización

- `pipeline_vectorial.py` y `prueba_sin_persistencia.py`: búsqueda con FAISS y comparación de persistencia.
- `migrar_chromadb.py` y `vector_db.py`: indexación y búsqueda híbrida en ChromaDB.
- `etl_purga.py`: normalización, colisiones de IDs y purga semántica.
- `evento_caliente.py` y `agregar_politica_vencida.py`: cambios de documentos en la colección histórica.
- `killer_queries.py`, `token_test.py` y `similitud_coseno.py`: pruebas y ejemplos de esta etapa.
- `base_conocimiento_sucia.json`, `base_conocimiento_limpia.json` y `log_etl_purga.md`: entrada y resultados del proceso de limpieza.
- `informe_entrega2.md`, `resultados_killer_queries.md` y `B4_Captura*.png`: documentación y evidencias originales.

## Rutas y ejecución

Ejecutar los scripts desde la raíz del repositorio, con el entorno activado. Estos scripts históricos usan imports entre archivos de la misma carpeta y se ejecutan como archivos:

```powershell
python entrega_2/similitud_coseno.py
python entrega_2/token_test.py
python entrega_2/pipeline_vectorial.py
python entrega_2/prueba_sin_persistencia.py
python entrega_2/etl_purga.py
python entrega_2/migrar_chromadb.py
python entrega_2/vector_db.py
python entrega_2/killer_queries.py
```

Salvo el ejemplo numérico de similitud coseno, los comandos anteriores requieren la clave y los modelos Gemini configurados en el `.env` de la raíz. No son necesarios para iniciar ni probar el agente local final.

Los scripts vectoriales utilizan la base compartida `base_conocimiento.json`, la colección histórica de `chroma_db/` y los artefactos FAISS de la raíz. El ETL lee y escribe sus archivos JSON y su log dentro de `entrega_2/`; no reemplaza automáticamente la base compartida.

Los scripts `evento_caliente.py` y `agregar_politica_vencida.py` modifican la colección histórica si se ejecutan. La colección local del agente final permanece separada en `entrega_4/chroma_ollama/`.

Los informes y resultados conservan las mediciones originales. Algunos ejemplos de comandos en el informe describen la ubicación de archivos previa a esta reorganización; los comandos de este README corresponden a la estructura actual.
