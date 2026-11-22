# Agente Inteligente TecnoSupply

Proyecto final integrador de IADS 3. Integra un agente ReAct con LangGraph, recuperación de conocimiento, herramientas de dominio, memoria SQLite, una API REST, observabilidad y guardrails. Los modelos de generación y embeddings se ejecutan localmente mediante Ollama.

## Arquitectura por capas

La implementación vigente está en `tecnosupply/`. Cada capa agrupa una responsabilidad:

| Ubicación | Responsabilidad |
|---|---|
| `tecnosupply/presentacion/` | Endpoints de FastAPI, contratos de entrada y salida con Pydantic y traducción de errores a HTTP. |
| `tecnosupply/aplicacion/` | Casos de uso, agente y herramientas, resolución de referencias conversacionales, guardrails y coordinación del registro de consultas. |
| `tecnosupply/dominio/` | Reglas de negocio y errores para validar solicitudes de reclamo. No depende de FastAPI, LangGraph ni SQLite. |
| `tecnosupply/infraestructura/` | Acceso a SQLite, búsqueda e indexación en ChromaDB, conexión con Ollama, checkpoints, logs y métricas. |
| `tecnosupply/config.py` | Rutas, modelos y parámetros compartidos. |
| `tecnosupply/main.py` | Punto de entrada: carga el entorno, configura las trazas, crea FastAPI y conecta las rutas. |
| `scripts/` | Comandos de reindexación y validación manual del agente. |
| `tests/` | Pruebas automáticas de memoria, operaciones y seguridad. |

Los endpoints llaman a servicios de aplicación. Estos aplican las reglas del dominio y utilizan los adaptadores de infraestructura para consultar o persistir datos.

```text
Cliente HTTP
    ↓
Presentación: FastAPI + Pydantic
    ↓
Aplicación: validación → agente y herramientas → protección de salida
    ├── Dominio: reglas de reclamos
    └── Infraestructura: Ollama, ChromaDB, SQLite y observabilidad
```

## Estructura principal

```text
DSI_Proyecto_Final/
├── tecnosupply/
│   ├── main.py
│   ├── config.py
│   ├── presentacion/
│   │   ├── api.py
│   │   └── schemas.py
│   ├── aplicacion/
│   │   ├── agente.py
│   │   ├── contexto_conversacion.py
│   │   ├── herramientas.py
│   │   ├── seguridad.py
│   │   ├── servicio_conocimiento.py
│   │   ├── servicio_consultas.py
│   │   └── servicio_operaciones.py
│   ├── dominio/
│   │   └── reglas_reclamos.py
│   └── infraestructura/
│       ├── base_operaciones.py
│       ├── conocimiento_chroma.py
│       ├── indexacion_chroma.py
│       ├── memoria_sqlite.py
│       ├── observabilidad.py
│       ├── ollama.py
│       ├── pedidos_sqlite.py
│       └── reclamos_sqlite.py
├── scripts/
│   ├── prueba_agente.py
│   ├── reindexar_ollama.py
│   └── security_tests.py
├── tests/
│   ├── test_memoria.py
│   ├── test_operaciones.py
│   └── test_seguridad.py
├── entrega_1/
├── entrega_2/
├── entrega_3/
├── entrega_4/
│   ├── informe.md
│   ├── ficha_tecnica.md
│   └── matriz_validacion.md
├── base_conocimiento.json
├── requirements.txt
├── .env.example
└── .gitignore
```

El esquema muestra los componentes principales. Las entregas anteriores conservan su material académico. Los datos locales del agente permanecen actualmente en `entrega_4/`; sus rutas están centralizadas en `tecnosupply/config.py`.

## Requisitos

- Python 3.12.
- Ollama instalado y ejecutándose.
- Una terminal PowerShell para seguir los ejemplos.
- Una clave de LangSmith si se desea enviar trazas a ese servicio.

## Instalación

Ejecutar desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Descargar los modelos locales:

```powershell
ollama pull qwen3:4b-instruct
ollama pull nomic-embed-text
ollama list
```

Si Ollama no está ejecutándose, iniciarlo antes de reindexar o consultar al agente. En una instalación sin servicio activo puede iniciarse con `ollama serve` en otra terminal.

Los comandos siguientes usan `python` del entorno virtual activado. Si el entorno existente del proyecto se llama `.venv_ragas`, también puede activarse con `.\.venv_ragas\Scripts\Activate.ps1`.

## Configuración y LangSmith

Crear `.env` desde el ejemplo, únicamente si todavía no existe:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

Para enviar trazas, configurar en `.env`:

```env
LANGSMITH_API_KEY=tu_clave_de_langsmith
```

El punto de entrada actual carga el `.env` de la raíz y habilita las trazas para el proyecto `tecnosupply-agente-entrega4`. La clave es opcional para la inferencia local y necesaria para enviar trazas a LangSmith. Mantener `.env` fuera de Git.

Los nombres de modelos, la URL de Ollama, las rutas de persistencia y el límite de ejecución se definen en `tecnosupply/config.py`.

## Preparar la base vectorial

Antes de la primera consulta de conocimiento:

```powershell
python -m scripts.reindexar_ollama
```

El comando lee `base_conocimiento.json`, genera embeddings con `nomic-embed-text` y realiza un `upsert` por identificador en la colección `conocimiento_tecnosupply_ollama`. La fuente del proyecto contiene 15 documentos. La colección se persiste en `entrega_4/chroma_ollama/`.

Generación y búsqueda utilizan el mismo modelo de embeddings. Si se cambia de modelo, debe reconstruirse una colección compatible antes de consultarla.

## Iniciar la API

Desde la raíz del repositorio, con el entorno activado:

```powershell
python -m uvicorn tecnosupply.main:app --port 8000
```

Para recarga automática durante desarrollo puede agregarse `--reload`.

- Documentación interactiva: [Swagger](http://127.0.0.1:8000/docs).
- Estado básico: [Health](http://127.0.0.1:8000/health).

Al cargar el agente se crean las tablas operativas si faltan y se insertan los pedidos de demostración que todavía no existen. Los registros existentes se conservan.

## Endpoints y memoria mediante HTTP

### `GET /health`

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health'
```

Devuelve el modelo configurado y comprueba la existencia de las rutas de memoria, operaciones y ChromaDB. Es una comprobación de configuración y archivos: no ejecuta una inferencia de prueba ni verifica la disponibilidad de Ollama.

### `POST /consultar`

Desde una segunda terminal PowerShell:

```powershell
$hilo = 'demo-memoria-001'
$body = @{
    consulta = '¿Cuál es el estado del pedido PED-1003?'
    thread_id = $hilo
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri 'http://127.0.0.1:8000/consultar' `
    -Method Post `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) |
    ConvertTo-Json -Depth 5
```

La respuesta incluye `thread_id`, `respuesta` y `herramientas_usadas`. Para PED-1003 se espera el producto Mouse Logitech MX Master y el estado en tránsito.

Enviar una pregunta de seguimiento con el mismo hilo:

```powershell
$body = @{
    consulta = '¿Cuál era el producto de ese pedido?'
    thread_id = $hilo
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri 'http://127.0.0.1:8000/consultar' `
    -Method Post `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) |
    ConvertTo-Json -Depth 5
```

Para seguimientos de producto o estado, la aplicación puede completar una referencia como “ese pedido” con la última mención inequívoca del usuario en el mismo hilo. El historial visible conserva la pregunta original. Esta resolución no elige entre varios pedidos ni completa solicitudes de acciones.

### `GET /estado/{thread_id}`

```powershell
Invoke-RestMethod `
    -Uri 'http://127.0.0.1:8000/estado/demo-memoria-001' |
    ConvertTo-Json -Depth 5
```

Devuelve el historial visible y enmascarado. Para demostrar persistencia, detener Uvicorn con `Ctrl+C`, volver a iniciarlo y consultar el mismo hilo. También puede enviarse otra pregunta de seguimiento con ese `thread_id`.

### `GET /metricas`

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/metricas' |
    ConvertTo-Json -Depth 5
```

Incluye consultas registradas, errores, bloqueos, latencia promedio, p95 y frecuencia de uso de herramientas. Las latencias agregadas corresponden a consultas con estado `ok`; p95 usa el método de rango más cercano. Los datos se acumulan en SQLite y sobreviven al reinicio.

## Herramientas y fundamentación

| Herramienta | Tipo | Fuente o efecto |
|---|---|---|
| `buscar_conocimiento` | Retriever | Recupera hasta tres documentos vigentes de ChromaDB. |
| `consultar_estado_pedido` | Sensor | Lee un pedido de la base operativa SQLite. |
| `registrar_reclamo` | Actuador | Inserta un reclamo para un pedido existente, con estado inicial `abierto`. |

Las respuestas de conocimiento se construyen a partir del contenido del primer documento recuperado. Las respuestas operativas se forman con los campos devueltos por las herramientas. El límite de ejecución del grafo se configura mediante `recursion_limit`, actualmente con valor 8; limita pasos del grafo, no equivale a ocho llamadas garantizadas al modelo.

Si el modelo no ejecuta ninguna herramienta, existe un fallback de lectura. Puede consultar un pedido identificado o recuperar conocimiento. Este fallback nunca ejecuta `registrar_reclamo`. Registrar un reclamo no aprueba una devolución, reemplazo ni reintegro.

## Pruebas automáticas

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```

La suite actual tiene 27 pruebas:

- 8 de referencias conversacionales, aislamiento del contexto proporcionado al resolver, selección del pedido y conservación de la pregunta original.
- 9 de consultas, validación, persistencia, integridad referencial y reinicialización de operaciones.
- 10 de guardrails, contratos HTTP, enmascarado, errores y registro de métricas.

Las llamadas al modelo se sustituyen por dobles de prueba. Las escrituras de operaciones y observabilidad se verifican con bases y logs temporales. Estas pruebas no generan inferencias ni reclamos en la base operativa habitual; la importación del agente puede inicializar los recursos locales que requiere su arranque.

Resultado esperado:

```text
Ran 27 tests ...
OK
```

Para ejecutar únicamente las 10 pruebas de seguridad:

```powershell
python -m scripts.security_tests
```

Este comando conserva el nombre `security_tests.py` solicitado por la consigna y carga las pruebas de `tests/test_seguridad.py`.

## Validación manual del agente

Con Ollama disponible y la colección ya indexada:

```powershell
python -m scripts.prueba_agente
```

Ejecuta los cuatro escenarios: conocimiento, sensor, actuador y memoria entre turnos. El escenario del actuador crea un reclamo simulado para PED-1004 en la base operativa local. Cada ejecución usa identificadores de conversación nuevos.

## Seguridad

Pydantic valida los tipos y campos requeridos del contrato HTTP. Los guardrails de aplicación rechazan consultas vacías, consultas de más de 1000 caracteres y patrones conocidos de prompt injection antes de ejecutar el agente. Un bloqueo controlado devuelve HTTP 400; los errores de esquema HTTP se responden con 422.

Las respuestas y el historial expuesto por HTTP se enmascaran mediante patrones de email, DNI, CUIT y teléfonos etiquetados. Estos controles basados en patrones tienen cobertura limitada y no sustituyen la autenticación ni la autorización. `thread_id` identifica una conversación; no acredita la identidad de un cliente.

Los pedidos y reclamos del proyecto son datos simulados para fines académicos.

## Persistencia y observabilidad

| Ruta local | Contenido |
|---|---|
| `entrega_4/operaciones.db` | Pedidos y reclamos. |
| `entrega_4/memoria_agente.sqlite` | Checkpoints de LangGraph por hilo. |
| `entrega_4/chroma_ollama/` | Documentos y embeddings de ChromaDB. |
| `entrega_4/observabilidad.sqlite` | Métricas persistentes de consultas. |
| `entrega_4/logs/agente.jsonl` | Eventos estructurados JSON Lines. |

Los logs de consulta registran longitud de entrada, hilo, latencia, estado, herramientas y errores o bloqueos. Las trazas de LangSmith permiten inspeccionar las etapas del grafo y las llamadas a herramientas. Los checkpoints y las trazas pueden contener contenido conversacional, aunque la salida HTTP esté enmascarada.

La inferencia local no genera cargos por tokens de un proveedor de modelos externo. Tiene costos de hardware, energía, almacenamiento y tiempo de ejecución. LangSmith es un servicio separado y su uso depende del plan y volumen de trazas.

Las bases, índices, logs, entornos virtuales y `.env` están excluidos mediante `.gitignore`. La base vectorial puede regenerarse; el historial de conversaciones y los reclamos requieren una copia de seguridad si se desea conservarlos.

## Documentación del trabajo

- [Primera entrega: clasificador de emails](entrega_1/informe.md).
- [Guía del material de la Entrega 2](entrega_2/README.md).
- [Informe de la entrega final](entrega_4/informe.md).
- [Ficha técnica](entrega_4/ficha_tecnica.md).
- [Matriz de validación](entrega_4/matriz_validacion.md).
- [Material de la Entrega 2](entrega_2/).
- [Material de la Entrega 3](entrega_3/).

## Tecnologías

Python 3.12, LangGraph, LangChain, Ollama, Qwen 3 4B Instruct, Nomic Embed Text, ChromaDB, SQLite, FastAPI, Pydantic, Uvicorn y LangSmith.
