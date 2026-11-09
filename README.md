# Agente Inteligente TecnoSupply

Proyecto final integrador de IADS 3. Convierte el RAG desarrollado previamente en un agente con LangGraph, herramientas de dominio, memoria persistente, API REST, observabilidad y controles de seguridad.

## Funcionalidades

- Agente ReAct implementado con LangGraph.
- Recuperación semántica sobre una base de conocimiento en ChromaDB.
- Consulta de estado operativo de pedidos.
- Registro persistente de reclamos de postventa.
- Memoria conversacional SQLite por `thread_id`.
- API REST con FastAPI.
- Logs JSON y métricas de operación.
- Trazas mediante LangSmith.
- Validadores contra prompt injection y consultas excesivamente largas.
- Enmascarado de datos personales en las respuestas.
- Pruebas automáticas de seguridad.

## Estructura principal

```text
DSI_Proyecto_Final/
├── base_conocimiento.json
├── requirements.txt
├── .env.example
├── .gitignore
├── entrega_2/
├── entrega_3/
└── entrega_4/
    ├── agente.py
    ├── herramientas.py
    ├── reindexar_ollama.py
    ├── api.py
    ├── observabilidad.py
    ├── seguridad.py
    ├── security_tests.py
    ├── prueba_agente.py
    ├── informe.md
    ├── ficha_tecnica.md
    └── README.md
```

Los directorios de ChromaDB, las bases SQLite, los logs y los entornos virtuales se generan localmente y están excluidos mediante `.gitignore`.

## Requisitos

- Python 3.12.
- Ollama instalado y ejecutándose.
- Acceso opcional a una cuenta de LangSmith para visualizar trazas.
- Windows PowerShell o una terminal compatible.

## Instalación desde cero

Ubicado en la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Instalar los modelos locales requeridos:

```powershell
ollama pull qwen3:4b-instruct
ollama pull nomic-embed-text
```

Verificar que Ollama esté disponible:

```powershell
ollama list
```

## Configuración de variables de entorno

Copiar el archivo de ejemplo:

```powershell
Copy-Item .env.example .env
```

Configurar estas variables en `.env`:

```env
LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=tecnosupply-agente-entrega4
```

`LANGSMITH_API_KEY` es opcional para ejecutar el agente, pero necesaria para enviar trazas a LangSmith. No subir `.env` al repositorio.

## Generación de la base vectorial local

Antes de utilizar el agente por primera vez, generar el índice vectorial local:

```powershell
python entrega_4/reindexar_ollama.py
```

La salida esperada informa que se indexaron los 15 documentos de `base_conocimiento.json` en:

```text
entrega_4/chroma_ollama/
```

## Prueba del agente

Ejecutar la matriz de validación:

```powershell
python entrega_4/prueba_agente.py
```

La prueba valida:

1. Recuperación de conocimiento de soporte.
2. Consulta del estado operativo de un pedido.
3. Registro de un reclamo.
4. Memoria persistente entre turnos mediante el mismo `thread_id`.

## Ejecutar la API REST

Desde la raíz del proyecto:

```powershell
python -m uvicorn entrega_4.api:app --reload --port 8000
```

La API queda disponible en:

- Documentación Swagger: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Endpoints

### `GET /health`

Comprueba que los recursos locales necesarios existan.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

### `POST /consultar`

Envía una consulta al agente.

```powershell
$body = @{
    consulta = "¿Cuál es el estado del pedido PED-1002?"
    thread_id = "demo-001"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/consultar" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body |
    ConvertTo-Json -Depth 5
```

### `GET /estado/{thread_id}`

Muestra el historial persistente de un hilo de conversación.

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/estado/demo-001" |
    ConvertTo-Json -Depth 5
```

Para demostrar persistencia, detener la API con `Ctrl + C`, volver a iniciarla y consultar nuevamente el mismo endpoint.

### `GET /metricas`

Devuelve métricas acumuladas de operación.

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/metricas" |
    ConvertTo-Json -Depth 5
```

Incluye cantidad de consultas, errores, bloqueos, latencia promedio, p95 y frecuencia de herramientas.

## Seguridad

La API integra los siguientes guardrails:

- Rechazo de consultas superiores a 1000 caracteres.
- Detección de patrones frecuentes de prompt injection.
- Enmascarado de emails, DNI, CUIT y teléfonos en la respuesta.
- Registro de bloqueos dentro de las métricas y logs.

Ejecutar las pruebas automáticas:

```powershell
python entrega_4/security_tests.py
```

La salida esperada finaliza con:

```text
Ran 5 tests ...
OK
```

## Observabilidad y LangSmith

Cada consulta se registra en:

```text
entrega_4/logs/agente.jsonl
entrega_4/observabilidad.sqlite
```

Las trazas de LangSmith permiten visualizar:

- Entrada del usuario.
- Decisión de herramientas.
- Argumentos enviados a cada herramienta.
- Resultado de las herramientas.
- Respuesta final.
- Latencia de ejecución.

El modelo se ejecuta localmente con Ollama. Por lo tanto, no hay costo variable de inferencia de un proveedor externo; el costo se concentra en el uso del equipo local.

## Notas de seguridad

- No incluir claves reales dentro del código ni en archivos versionados.
- `.env`, bases SQLite, logs y bases vectoriales deben permanecer ignorados por Git.
- El registro de un reclamo no aprueba automáticamente devolución, reemplazo ni reintegro.
- La información de pedidos y reclamos corresponde a datos simulados para fines académicos.

## Tecnologías

- Python 3.12
- LangGraph
- LangChain
- Ollama
- Qwen 3 4B Instruct
- Nomic Embed Text
- ChromaDB
- SQLite
- FastAPI
- Uvicorn
- LangSmith