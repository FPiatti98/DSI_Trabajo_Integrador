# Informe — TP Final Integrador  
## Agente Inteligente en Producción: TecnoSupply Argentina

## Introducción

Este trabajo transforma el sistema RAG desarrollado en la Entrega 3 en un agente inteligente orientado al dominio de atención al cliente de TecnoSupply Argentina.

La solución incorpora un agente ReAct con LangGraph, herramientas de consulta y acción, memoria conversacional persistente, una API REST, trazabilidad, métricas operativas y guardrails de seguridad. El sistema utiliza modelos locales mediante Ollama, por lo que puede ejecutarse sin depender de cuotas de un proveedor externo para generar respuestas o embeddings.

---

# A. Agente

## A.1 Arquitectura general

El agente se implementó con el patrón ReAct mediante LangGraph. Recibe una consulta del usuario, decide qué herramienta utilizar, obtiene evidencia o datos operativos y genera una respuesta fundamentada.

El modelo generador utilizado es `qwen3:4b-instruct` mediante Ollama. La recuperación semántica utiliza embeddings locales del modelo `nomic-embed-text` y una colección persistente de ChromaDB.

La ejecución del grafo tiene un límite de 8 iteraciones para evitar ciclos o ejecuciones indefinidas.

```text
Usuario
  ↓
Agente ReAct con LangGraph
  ├── buscar_conocimiento
  ├── consultar_estado_pedido
  └── registrar_reclamo
  ↓
Respuesta fundamentada
  ↓
Memoria SQLite por thread_id
```

## A.2 Herramientas implementadas

| Herramienta | Tipo | Descripción |
|---|---|---|
| `buscar_conocimiento` | Retriever | Recupera documentos vigentes de la base de conocimiento mediante búsqueda semántica sobre ChromaDB. |
| `consultar_estado_pedido` | Sensor | Consulta el estado operativo actual de un pedido desde la base SQLite de operaciones. |
| `registrar_reclamo` | Actuador | Crea un reclamo de postventa persistente para un pedido existente. |

Las tres herramientas poseen docstrings con su propósito, parámetros, tipo de salida y restricciones de seguridad.

La herramienta de reclamos informa expresamente que registrar un reclamo no implica aprobar automáticamente una devolución, reemplazo ni reintegro.

## A.3 Memoria persistente

La memoria se implementó con `SqliteSaver` de LangGraph. Cada conversación se asocia a un `thread_id`, lo que permite conservar el contexto entre turnos e incluso luego de reiniciar la aplicación.

El archivo local `memoria_agente.sqlite` almacena los checkpoints de la conversación. Este archivo no se versiona, ya que se genera localmente.

## A.4 Matriz de validación

| Escenario | Objetivo | Resultado observado |
|---|---|---|
| 1. Retriever de conocimiento | Resolver una consulta de soporte sobre una notebook que no enciende. | Se recuperó el documento `DOC-010` y se respondió utilizando la evidencia de cargador, conexión eléctrica e indicadores luminosos. |
| 2. Sensor de pedidos | Consultar el estado del pedido `PED-1002`. | Se informó correctamente que el pedido estaba despachado y que correspondía a un Monitor Samsung de 24 pulgadas. |
| 3. Actuador de reclamos | Registrar un reclamo explícito para `PED-1004`. | El sistema creó el reclamo, devolvió su número, estado `abierto` y aclaró que no implica aprobación automática. |
| 4. Memoria por `thread_id` | Recordar el pedido mencionado en un turno anterior. | Luego de consultar `PED-1003`, el agente respondió correctamente cuál era el producto del pedido: Mouse Logitech MX Master. |

La matriz fue ejecutada mediante `prueba_agente.py`. Los cuatro escenarios finalizaron correctamente.

---

# B. API REST

## B.1 Endpoints implementados

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Comprueba disponibilidad del modelo, memoria SQLite, base operativa, ChromaDB y seguridad. |
| `POST` | `/consultar` | Procesa una consulta mediante el agente. |
| `GET` | `/estado/{thread_id}` | Devuelve el historial persistente de una conversación. |
| `GET` | `/metricas` | Devuelve métricas operativas acumuladas. |

La API se implementó con FastAPI y se documenta automáticamente mediante Swagger en:

```text
http://127.0.0.1:8000/docs
```

## B.2 Consulta mediante HTTP

Se realizó una consulta HTTP utilizando el siguiente cuerpo:

```json
{
  "consulta": "¿Cuál es el estado del pedido PED-1003?",
  "thread_id": "api-memoria-001"
}
```

El agente informó que el pedido se encontraba en tránsito y que el producto era un Mouse Logitech MX Master.

Luego se envió una segunda consulta con el mismo `thread_id`:

```json
{
  "consulta": "¿Cuál era el producto de ese pedido?",
  "thread_id": "api-memoria-001"
}
```

La respuesta recuperó correctamente el producto mencionado en el turno anterior.

## B.3 Persistencia después de reiniciar

La API se detuvo y se volvió a iniciar. Posteriormente, se consultó:

```text
GET /estado/api-memoria-001
```

El endpoint devolvió los cuatro mensajes de la conversación: dos mensajes del usuario y dos respuestas del asistente. Esto demuestra que la memoria no depende del proceso activo de FastAPI, sino que permanece persistida en SQLite.

---

# C. Observabilidad

## C.1 Logs estructurados

Cada consulta se registra en:

```text
entrega_4/logs/agente.jsonl
```

Cada línea corresponde a un evento JSON independiente e incluye:

- Fecha y hora en UTC.
- Identificador de conversación.
- Longitud de la consulta.
- Latencia total.
- Estado de procesamiento.
- Herramientas utilizadas.
- Indicación de bloqueo de seguridad.
- Detalle resumido del error, cuando corresponde.

Además, las métricas se almacenan en la base SQLite:

```text
entrega_4/observabilidad.sqlite
```

## C.2 Métricas expuestas

El endpoint `GET /metricas` devolvió el siguiente estado acumulado:

| Métrica | Valor |
|---|---:|
| Consultas registradas | 19 |
| Errores registrados | 4 |
| Bloqueos de seguridad | 1 |
| Latencia promedio | 12992.40 ms |
| Latencia p95 | 45074.98 ms |
| Uso de `consultar_estado_pedido` | 5 |
| Uso de `registrar_reclamo` | 1 |
| Uso de `buscar_conocimiento` | 1 |

Las métricas son persistentes y acumulativas. Por este motivo, los errores registrados incluyen pruebas de desarrollo previas a la corrección final de los guardrails y de la API. La ejecución final de la suite automática de seguridad concluyó correctamente con cinco pruebas aprobadas.

La latencia observada se explica principalmente por la inferencia local de `qwen3:4b-instruct` mediante Ollama. El valor p95 es mayor que el promedio porque representa una de las consultas más lentas del conjunto acumulado.

## C.3 Trazabilidad con LangSmith

Se configuró LangSmith con el proyecto:

```text
tecnosupply-agente-entrega4
```

La traza generada para la consulta del estado de `PED-1002` permite observar:

1. La entrada del usuario.
2. La decisión del agente de invocar `consultar_estado_pedido`.
3. El argumento enviado: `PED-1002`.
4. La respuesta estructurada de la herramienta.
5. La respuesta final entregada al usuario.

Esto permite auditar la decisión del agente y verificar que la respuesta se basó en datos operativos reales de la herramienta.

## C.4 Análisis de costos

El modelo generador y el modelo de embeddings se ejecutan localmente mediante Ollama. Por lo tanto, el sistema no genera un costo variable por consulta a un proveedor de modelos externo.

El costo operativo se concentra en:

- Tiempo de inferencia local.
- Uso de CPU, GPU y memoria del equipo.
- Almacenamiento de ChromaDB, SQLite y logs.

LangSmith se utiliza para observabilidad de trazas. Su costo depende del plan y del volumen de trazas almacenadas, no de la generación realizada por Ollama.

---

# D. Seguridad

## D.1 Validadores de entrada

Se integraron dos validadores antes de ejecutar el agente:

| Validador | Comportamiento |
|---|---|
| Longitud máxima | Rechaza consultas de más de 1000 caracteres. |
| Prompt injection | Bloquea patrones como ignorar instrucciones, omitir reglas, actuar como otro rol, revelar el prompt, jailbreak, DAN o bypass. |

Cuando un validador bloquea una consulta, la API devuelve el estado HTTP `400`, no llama al agente y registra el bloqueo en observabilidad.

## D.2 Validador de salida

Antes de devolver una respuesta al usuario, el sistema ejecuta un enmascarado de datos personales. Se ocultan:

- Direcciones de email.
- DNI.
- CUIT.
- Números telefónicos etiquetados.

Ejemplos de reemplazo:

```text
ana.perez@correo.com → [EMAIL_OCULTO]
DNI: 12345678 → DNI: [DNI_OCULTO]
CUIT: 20-12345678-9 → CUIT: [CUIT_OCULTO]
Teléfono: 11 5555-1234 → TELÉFONO: [TELÉFONO_OCULTO]
```

## D.3 Suite automática de pruebas

La suite `security_tests.py` ejecutó cinco pruebas automáticas y finalizó correctamente:

```text
Ran 5 tests in 0.056s

OK
```

| Prueba | Resultado |
|---|---|
| Bloqueo de prompt injection | Aprobada |
| Bloqueo por longitud excesiva | Aprobada |
| Enmascarado de datos personales | Aprobada |
| Bloqueo desde `POST /consultar` antes de invocar el agente | Aprobada |
| Enmascarado de la salida desde la API | Aprobada |

---

# Conclusión

El proyecto implementa un agente de atención al cliente funcional y observable para TecnoSupply Argentina. La solución integra recuperación semántica, herramientas de dominio, memoria persistente, una API REST, trazabilidad y controles de seguridad.

El agente puede responder consultas basadas en conocimiento vigente, consultar el estado de pedidos y registrar reclamos. La memoria SQLite permite sostener conversaciones por `thread_id`, mientras que FastAPI expone estas capacidades mediante endpoints documentados.

La observabilidad permite monitorear latencia, errores, bloqueos y uso de herramientas. Finalmente, los guardrails validan la entrada y protegen la salida para reducir riesgos de prompt injection y exposición de datos personales.
