# Ficha técnica — Agente Inteligente TecnoSupply

## 1. Identificación

| Campo | Descripción |
|---|---|
| Sistema | Agente Inteligente TecnoSupply |
| Dominio | Atención al cliente para comercio tecnológico |
| Arquitectura | Agente ReAct con LangGraph, RAG local, memoria SQLite y API REST |
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

Esto permite que el agente recuerde información mencionada en turnos previos, incluso después de reiniciar la API. Por ejemplo, luego de consultar el estado de `PED-1003`, el usuario puede preguntar “¿Cuál era el producto de ese pedido?” y el agente conserva el contexto.

Archivos persistentes principales:

| Archivo o directorio | Propósito |
|---|---|
| `memoria_agente.sqlite` | Checkpoints e historial conversacional de LangGraph. |
| `operaciones.db` | Pedidos operativos y reclamos registrados. |
| `chroma_ollama/` | Base vectorial local persistente de ChromaDB. |
| `observabilidad.sqlite` | Métricas históricas de la API. |
| `logs/agente.jsonl` | Eventos estructurados en formato JSON Lines. |

Estos artefactos se excluyen del repositorio mediante `.gitignore`, ya que se reconstruyen o generan localmente.

## 6. API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Verifica disponibilidad del modelo, memoria, base operativa, ChromaDB y seguridad. |
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

La suite `security_tests.py` valida automáticamente estos controles. La ejecución final aprobó cinco pruebas.

## 9. Limitaciones conocidas

- El modelo local `qwen3:4b-instruct` puede presentar variabilidad en la redacción o en la elección inicial de una herramienta.
- Se incorporó una protección para consultas de lectura: si el modelo no invoca una herramienta de lectura necesaria, el sistema recupera evidencia de forma controlada. El actuador `registrar_reclamo` nunca se ejecuta automáticamente mediante esta protección.
- La base de operaciones utilizada es una simulación local para fines académicos.
- El sistema no reemplaza validaciones comerciales, administrativas ni humanas requeridas por TecnoSupply.

## 10. Mejoras futuras

- Incorporar autenticación y autorización por usuario.
- Conectar la base operativa a un sistema transaccional real.
- Implementar confirmación explícita antes de ejecutar acciones sensibles.
- Agregar métricas de calidad de respuesta y evaluación humana.
- Ampliar los detectores de prompt injection y datos personales.
- Contenerizar el sistema para facilitar el despliegue reproducible.