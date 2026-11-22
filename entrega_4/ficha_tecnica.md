# Ficha técnica — Agente Inteligente TecnoSupply

## 1. Identificación

| Campo | Descripción |
|---|---|
| Sistema | Agente Inteligente TecnoSupply |
| Dominio | Atención al cliente para comercio tecnológico |
| Arquitectura | Organización por capas con agente ReAct de LangGraph, RAG local, memoria SQLite y API REST |
| Modelo generador | `qwen3:4b-instruct` mediante Ollama |
| Modelo de embeddings | `nomic-embed-text` mediante Ollama |
| Base vectorial | ChromaDB persistente |
| Memoria conversacional | SQLite persistente por `thread_id` |
| Framework API | FastAPI |
| Observabilidad | Logs JSON, SQLite de métricas y LangSmith |
| Seguridad | Validación de entrada y enmascarado de datos personales |

## 2. Objetivo del sistema

El sistema asiste consultas de clientes de TecnoSupply Argentina. Puede recuperar información vigente desde la base de conocimiento, consultar el estado operativo de un pedido y registrar reclamos de postventa.

El agente no confirma operaciones que requieran validación humana, como devoluciones, reemplazos, reintegros o cambios administrativos definitivos.

## 3. Arquitectura

El código vigente está en `tecnosupply/` y se divide en:

| Componente | Función |
|---|---|
| `presentacion/` | Endpoints HTTP, esquemas Pydantic y respuestas de error. |
| `aplicacion/` | Servicios, agente, herramientas, guardrails y referencias conversacionales. |
| `dominio/` | Reglas de negocio y errores de validación de reclamos. |
| `infraestructura/` | Ollama, ChromaDB, SQLite, checkpoints y observabilidad. |
| `config.py` | Rutas y parámetros compartidos. |
| `main.py` | Composición y arranque de la API. |

Los comandos se agrupan en `scripts/`, las pruebas automáticas en `tests/` y el material académico en `entrega_1/` a `entrega_4/`.

```text
Cliente HTTP
    ↓
FastAPI: POST /consultar
    ↓
Guardrails de entrada
    ├── Límite de longitud
    └── Detección de prompt injection
    ↓
Agente ReAct (LangGraph)
    ├── buscar_conocimiento → ChromaDB + embeddings locales
    ├── consultar_estado_pedido → SQLite de operaciones
    └── registrar_reclamo → SQLite de operaciones
    ↓
Memoria persistente SQLite por thread_id
    ↓
Guardrail de salida: ocultamiento de datos personales
    ↓
Respuesta HTTP + logs JSON + métricas + trazas LangSmith
```

## 4. Herramientas del agente

| Herramienta | Tipo | Función |
|---|---|---|
| `buscar_conocimiento` | Retriever | Recupera documentos vigentes de la base de conocimiento mediante búsqueda semántica en ChromaDB. |
| `consultar_estado_pedido` | Sensor | Consulta el estado actual de un pedido desde la base operativa SQLite. |
| `registrar_reclamo` | Actuador | Registra un reclamo de postventa asociado a un pedido existente. |

Las herramientas incluyen docstrings con propósito, parámetros, salida y restricciones de seguridad.

## 5. Memoria y persistencia

La memoria conversacional se implementa mediante `SqliteSaver` de LangGraph y se asocia a cada conversación a través de `thread_id`.

Esto permite recuperar el contexto persistido de un hilo, incluso después de reiniciar la API. Para seguimientos de producto o estado como “¿Cuál era el producto de ese pedido?”, la aplicación completa la referencia con la última mención inequívoca del usuario en ese hilo. La pregunta original se conserva en el historial visible. No se elige automáticamente entre varios pedidos ni se completan solicitudes de acciones.

Archivos persistentes principales:

| Archivo o directorio | Propósito |
|---|---|
| `memoria_agente.sqlite` | Checkpoints e historial conversacional de LangGraph. |
| `operaciones.db` | Pedidos operativos y reclamos registrados. |
| `chroma_ollama/` | Base vectorial local persistente de ChromaDB. |
| `observabilidad.sqlite` | Métricas históricas de la API. |
| `logs/agente.jsonl` | Eventos estructurados en formato JSON Lines. |

Estos artefactos permanecen localmente bajo `entrega_4/`, con rutas centralizadas en `tecnosupply/config.py`, y se excluyen del repositorio mediante `.gitignore`. La colección vectorial puede regenerarse; los reclamos y el historial requieren respaldo si se desea conservarlos.

## 6. API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Informa el modelo configurado y la existencia de las rutas locales principales. No ejecuta una inferencia de prueba. |
| `POST` | `/consultar` | Procesa una consulta del usuario mediante el agente. |
| `GET` | `/estado/{thread_id}` | Recupera el historial persistente de una conversación. |
| `GET` | `/metricas` | Devuelve consultas, errores, bloqueos, latencia promedio, p95 y frecuencia de herramientas. |

Ejemplo de cuerpo para `POST /consultar`:

```json
{
  "consulta": "¿Cuál es el estado del pedido PED-1002?",
  "thread_id": "cliente-001"
}
```

## 7. Observabilidad

El sistema registra cada consulta procesada en dos medios persistentes:

- Archivo JSON Lines: contiene eventos con fecha UTC, thread, longitud de consulta, latencia, estado, herramientas utilizadas y bloqueos.
- SQLite: permite calcular métricas acumuladas mediante el endpoint `/metricas`.

Las métricas disponibles son:

- Cantidad de consultas.
- Cantidad de errores.
- Cantidad de bloqueos de seguridad.
- Latencia promedio.
- Latencia p95.
- Frecuencia de uso de cada herramienta.

Además, LangSmith registra las trazas del agente, sus decisiones de herramientas, entradas, salidas y latencia. El modelo generador se ejecuta localmente mediante Ollama, por lo que no tiene costo variable por consulta de proveedor; el costo operativo se concentra en recursos locales de hardware y tiempo de inferencia.

## 8. Seguridad

Se implementaron tres controles integrados en la API:

| Control | Tipo | Descripción |
|---|---|---|
| Longitud máxima | Entrada | Rechaza consultas de más de 1000 caracteres. |
| Detección de prompt injection | Entrada | Bloquea intentos de ignorar reglas, revelar prompts, jailbreak, bypass y patrones similares. |
| Enmascarado de PII | Salida | Oculta emails, DNI, CUIT y teléfonos etiquetados antes de devolver una respuesta. |

El comando `python -m scripts.security_tests` ejecuta las 10 pruebas de `tests/test_seguridad.py`. La suite completa de la arquitectura por capas aprobó 27 pruebas: 10 de seguridad y HTTP, 9 de operaciones y 8 de memoria y referencias. Las llamadas al modelo se sustituyen por dobles de prueba; las escrituras de las pruebas usan bases y logs temporales.

## 9. Limitaciones conocidas

- El modelo local `qwen3:4b-instruct` puede presentar variabilidad en la redacción o en la elección inicial de una herramienta.
- Si el modelo no ejecuta ninguna herramienta, se aplica un fallback de lectura para consultar un pedido identificado o buscar conocimiento. El actuador `registrar_reclamo` nunca se ejecuta mediante este fallback.
- La resolución explícita de referencias conversacionales cubre seguimientos de producto o estado sobre un pedido inequívoco; no resuelve todas las formas posibles de referencia.
- El límite `recursion_limit=8` acota pasos del grafo y no equivale a ocho llamadas al modelo.
- La base de operaciones utilizada es una simulación local para fines académicos.
- El sistema no reemplaza validaciones comerciales, administrativas ni humanas requeridas por TecnoSupply.

## 10. Mejoras futuras

- Incorporar autenticación y autorización por usuario.
- Conectar la base operativa a un sistema transaccional real.
- Implementar confirmación explícita antes de ejecutar acciones sensibles.
- Agregar métricas de calidad de respuesta y evaluación humana.
- Ampliar los detectores de prompt injection y datos personales.
- Contenerizar el sistema para facilitar el despliegue reproducible.

## 11. Ejecución

Desde la raíz del repositorio, con el entorno virtual activado y Ollama disponible:

```powershell
python -m scripts.reindexar_ollama
python -m uvicorn tecnosupply.main:app --port 8000
```

La reindexación se requiere para preparar la colección o actualizarla cuando cambia la fuente. Las instrucciones completas de instalación, uso HTTP y validación están en el [README principal](../README.md).
