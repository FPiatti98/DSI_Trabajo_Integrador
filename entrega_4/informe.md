## B. API REST

Se implementó una API REST con FastAPI para exponer el agente TecnoSupply mediante HTTP.

| Endpoint | Método | Función |
|---|---|---|
| `/health` | GET | Verifica la disponibilidad del modelo local, ChromaDB, SQLite de operaciones y SQLite de memoria. |
| `/consultar` | POST | Recibe una consulta y un `thread_id`, ejecuta el agente ReAct y devuelve su respuesta. |
| `/estado/{thread_id}` | GET | Recupera el historial visible persistido de una conversación. |

La API se ejecuta desde la raíz del proyecto con:

```powershell
python -m uvicorn entrega_4.api:app --reload --port 8000
```

La documentación interactiva de FastAPI está disponible en:

```text
http://127.0.0.1:8000/docs
```

### Verificación de salud

La llamada a `GET /health` devolvió:

```json
{
  "estado": "ok",
  "modelo": "qwen3:4b-instruct",
  "memoria_sqlite": true,
  "base_operaciones": true,
  "chroma_local": true
}
```

Este resultado confirma que el modelo local, la memoria SQLite, la base de operaciones y la colección Chroma local estaban disponibles.

### Demostración de memoria vía HTTP

Se realizó una primera consulta mediante `POST /consultar` con el identificador de conversación `api-memoria-001`:

```json
{
  "consulta": "¿Cuál es el estado del pedido PED-1003?",
  "thread_id": "api-memoria-001"
}
```

El sistema respondió que el pedido `PED-1003` se encontraba en tránsito y correspondía a un Mouse Logitech MX Master.

Luego se realizó una segunda consulta utilizando el mismo `thread_id`:

```json
{
  "consulta": "¿Cuál era el producto de ese pedido?",
  "thread_id": "api-memoria-001"
}
```

El agente respondió correctamente que el producto era un Mouse Logitech MX Master, sin requerir nuevamente el número de pedido.

Finalmente, se reinició el servidor Uvicorn y se ejecutó:

```text
GET /estado/api-memoria-001
```

El endpoint devolvió los cuatro mensajes persistidos:

```json
{
  "thread_id": "api-memoria-001",
  "cantidad_mensajes": 4,
  "historial": [
    {
      "rol": "usuario",
      "contenido": "¿Cuál es el estado del pedido PED-1003?"
    },
    {
      "rol": "asistente",
      "contenido": "El pedido PED-1003 se encuentra en tránsito. El producto es Mouse Logitech MX Master. La última actualización fue 2026-11-03 09:40."
    },
    {
      "rol": "usuario",
      "contenido": "¿Cuál era el producto de ese pedido?"
    },
    {
      "rol": "asistente",
      "contenido": "El producto del pedido PED-1003 era un Mouse Logitech MX Master."
    }
  ]
}
```

La respuesta fue inmediata porque `GET /estado` consulta directamente los checkpoints guardados en `memoria_agente.sqlite`; no necesita volver a invocar Ollama ni ChromaDB. La persistencia del historial luego del reinicio demuestra que la memoria depende del `thread_id` y de SQLite, no del proceso activo.