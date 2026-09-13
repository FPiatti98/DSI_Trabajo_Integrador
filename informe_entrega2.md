# Proyecto Final — Sistema Inteligente de Clasificación de Emails Empresariales

# Parte A — Embeddings y Búsqueda Semántica

## A.1 — Autopsia del contexto estático

En TecnoSupply Argentina, la Base de Conocimiento contendrá inicialmente al menos 15 documentos relacionados con políticas de envíos, devoluciones, facturación, garantías, soporte técnico, productos y horarios de atención. Incluir todos estos documentos dentro del System Prompt en cada consulta no representa una solución escalable.

| Problema | Aplicado al dominio de TecnoSupply Argentina |
|---|---|
| **Desangre de tokens** | La base inicial contiene al menos 15 documentos y crecerá a medida que se agreguen nuevas políticas, productos y procedimientos. Si todos los documentos se envían en cada consulta, se consumen tokens aunque la mayoría no sea relevante. Esto aumenta el costo y la latencia de cada clasificación o respuesta. |
| **Lost in the Middle** | Una política importante, como el procedimiento para devolver una notebook dañada, puede quedar entre documentos sobre facturación, envíos y horarios de atención. Aunque esté presente en el prompt, el modelo puede no priorizarla correctamente dentro de un bloque extenso de texto. |
| **Inconsistencia de estado concurrente** | El estado de un pedido, el stock disponible, la fecha estimada de entrega y la disponibilidad de un producto pueden cambiar mientras el cliente mantiene una conversación. Un prompt estático puede contener información desactualizada y producir una respuesta incorrecta. |

Una consulta SQL como `SELECT ... WHERE descripcion LIKE '%...%'` tampoco resuelve este problema porque busca coincidencias textuales exactas. Un cliente puede expresar la misma necesidad con sinónimos, lenguaje informal, errores ortográficos o frases distintas, por ejemplo “mi compu no prende” en lugar de “soporte técnico para notebook”. La búsqueda semántica permite recuperar documentos según su significado y no solo por palabras idénticas.

## A.2 — Similitud coseno a mano

Para representar de forma simplificada el dominio de TecnoSupply Argentina se definieron dos ejes semánticos:

- **Eje X:** relación con pedidos, envíos y logística.
- **Eje Y:** relación con soporte técnico de productos.

Se representan los siguientes documentos y consulta mediante vectores bidimensionales:

| Elemento | Descripción | Vector |
|---|---|---|
| Documento 1 | Política de seguimiento y entrega de pedidos. | `D1 = (0.95, 0.10)` |
| Documento 2 | Guía de soporte para notebooks que no encienden. | `D2 = (0.15, 0.95)` |
| Documento 3 | Política de devolución de productos dañados. | `D3 = (0.65, 0.40)` |
| Consulta | “Mi notebook no enciende y necesito asistencia técnica.” | `Q = (0.10, 0.98)` |

La fórmula utilizada es:

```text
Similitud coseno = (A · B) / (||A|| × ||B||)
```

### Comparación entre la consulta y el Documento 1

**Paso 1 — Producto punto**

```text
Q · D1 = (0.10 × 0.95) + (0.98 × 0.10)
Q · D1 = 0.193
```

**Paso 2 — Magnitudes**

```text
||Q|| = √(0.10² + 0.98²) = 0.985

||D1|| = √(0.95² + 0.10²) = 0.955
```

**Paso 3 — Similitud coseno**

```text
Similitud(Q, D1) = 0.193 / (0.985 × 0.955)

Similitud(Q, D1) = 0.205
```

### Comparación entre la consulta y el Documento 2

**Paso 1 — Producto punto**

```text
Q · D2 = (0.10 × 0.15) + (0.98 × 0.95)
Q · D2 = 0.946
```

**Paso 2 — Magnitudes**

```text
||Q|| = 0.985

||D2|| = √(0.15² + 0.95²) = 0.962
```

**Paso 3 — Similitud coseno**

```text
Similitud(Q, D2) = 0.946 / (0.985 × 0.962)

Similitud(Q, D2) = 0.999
```

### Comparación entre la consulta y el Documento 3

**Paso 1 — Producto punto**

```text
Q · D3 = (0.10 × 0.65) + (0.98 × 0.40)
Q · D3 = 0.457
```

**Paso 2 — Magnitudes**

```text
||Q|| = 0.985

||D3|| = √(0.65² + 0.40²) = 0.763
```

**Paso 3 — Similitud coseno**

```text
Similitud(Q, D3) = 0.457 / (0.985 × 0.763)

Similitud(Q, D3) = 0.608
```

### Resultado

| Documento | Similitud coseno con la consulta |
|---|---:|
| Documento 1 — Seguimiento de pedidos | 0.205 |
| Documento 2 — Soporte para notebook | 0.999 |
| Documento 3 — Devoluciones | 0.608 |

El Documento 2 es el más similar porque está relacionado directamente con soporte técnico para una notebook que no enciende.

### Validación con NumPy

```python
import numpy as np

def similitud_coseno(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

documento_1 = np.array([0.95, 0.10])
documento_2 = np.array([0.15, 0.95])
documento_3 = np.array([0.65, 0.40])
consulta = np.array([0.10, 0.98])

print("D1:", similitud_coseno(consulta, documento_1))
print("D2:", similitud_coseno(consulta, documento_2))
print("D3:", similitud_coseno(consulta, documento_3))
```

La ejecución con NumPy devuelve aproximadamente los siguientes valores:

```text
D1: 0.205
D2: 0.999
D3: 0.608
```

Los resultados obtenidos con NumPy coinciden con los cálculos realizados manualmente.

### Umbral de aceptación

Para este sistema se podría utilizar inicialmente un umbral de aceptación de `0.80`. Un documento con un score igual o superior a ese valor se considera suficientemente relacionado con la consulta; por debajo de ese umbral no debería utilizarse como fuente confiable para responder.

Si ningún documento supera el umbral, el sistema no debe inventar una respuesta. Debe solicitar más información al cliente, derivar el caso a un empleado o responder que no cuenta con información suficiente.

## A.3 — Base de Conocimiento

La Base de Conocimiento de TecnoSupply Argentina se implementa mediante el archivo `base_conocimiento.json`, compuesto por 15 documentos relacionados con pedidos, envíos, reclamos, facturación, garantía, soporte técnico, stock, pagos, retiro en sucursal y horarios de atención.

Cada documento contiene un identificador, una `descripcion_semantica` redactada como un párrafo con contexto y vocabulario del dominio, y un bloque de `metadatos`.

Se aplicó la Regla del Arquitecto para definir el esquema. Los campos que pueden requerir filtros exactos se guardan como metadatos: `categoria` permite filtrar por tipo de información, `vigente` indica si el documento puede utilizarse y `sucursal` permite restringir información según la ubicación. El campo `tags_regionales` incorpora términos locales, sinónimos y expresiones habituales en Argentina.

La información narrativa, como procedimientos, condiciones, explicaciones y matices de cada política, se mantiene en `descripcion_semantica`. Este campo será transformado en embeddings para permitir búsquedas por significado.

## A.5 — Prueba destructiva: volatilidad de la RAM

### Prueba sin persistencia

Se creó el script `prueba_sin_persistencia.py`, que genera los embeddings de los 15 documentos y construye un índice `IndexFlatL2` únicamente en memoria RAM. El script no utiliza `faiss.write_index()` ni guarda ningún archivo de índice.

Al ejecutar el programa por primera vez se obtuvo el siguiente resultado:

```text
Generando embeddings y construyendo el índice solamente en RAM...
Índice creado en RAM con 15 documentos.
No se ejecutó faiss.write_index().
Al finalizar este programa, el índice se perderá.
```

Luego de finalizar el programa y ejecutar nuevamente el mismo script, fue necesario generar otra vez los embeddings y reconstruir el índice. Esto demuestra que el índice almacenado solamente en RAM se pierde cuando termina o se reinicia el proceso.

### Prueba con persistencia

Luego se ejecutó `pipeline_vectorial.py`, que utiliza `faiss.write_index()` para guardar el índice en el archivo `indice_faiss.index`.

En una ejecución posterior, el sistema mostró:

```text
Índice FAISS cargado desde disco. No se generaron embeddings nuevos.
```

Además, el archivo `documentos_indexados.json` permitió recuperar la relación entre las posiciones de los vectores y los documentos originales de la base de conocimiento.

### Conclusión

En producción, si el servidor se reinicia y el índice existe solamente en RAM, se pierde y deben regenerarse los embeddings, lo cual agrega demora y consumo de recursos. Si existen dos servidores, ambos deben acceder a un almacenamiento compartido o a una base vectorial centralizada; de lo contrario, cada servidor podría tener una versión distinta o incompleta del índice.

# Parte B — ChromaDB, Filtrado Híbrido y ETL (Clase 5)

## B.1 — Migración a ChromaDB

Se migró la misma base de conocimiento utilizada en A.3, compuesta por 15 documentos, a una colección persistente de ChromaDB denominada `conocimiento_tecnosupply`.

La conexión se realizó mediante `chromadb.PersistentClient`, con la ruta local `chroma_db/`. De esta forma, la colección y sus vectores permanecen disponibles en disco luego de finalizar el programa.

La colección fue creada con la configuración:

```python
metadata={"hnsw:space": "cosine"}
```

Se utilizaron los embeddings generados previamente con el modelo `gemini-embedding-001`. Cada registro fue almacenado con:

- `id`: identificador único del documento.
- `document`: contenido de `descripcion_semantica`.
- `embedding`: vector generado por Gemini.
- `metadata`: categoría, vigencia, sucursal y tags regionales.

La inserción se realizó mediante `upsert` en lugar de `add`. Esto permite ejecutar nuevamente el proceso de migración sin duplicar documentos: si un identificador ya existe, ChromaDB actualiza ese registro.

La ejecución informó que la colección contiene 15 documentos. Al repetir la ejecución, la cantidad se mantuvo en 15, verificando que no se generaron duplicados.

## B.2 — Los tres límites de FAISS que ChromaDB resuelve

| Límite de FAISS | Cómo se manifiesta en TecnoSupply Argentina | Cómo lo resuelve ChromaDB |
|---|---|---|
| Sin persistencia transaccional / atomicidad | Con FAISS fue necesario guardar por separado el índice `indice_faiss.index` y el archivo `documentos_indexados.json` que relaciona cada vector con su documento. Si uno se actualizara y el otro no, podrían quedar inconsistencias entre vectores, documentos y metadatos. | ChromaDB guarda documentos, embeddings, identificadores y metadatos dentro de una misma colección persistente. La operación `upsert` actualiza el registro completo asociado a un ID, reduciendo el riesgo de desincronización entre el vector y su información. |
| Sin filtrado híbrido nativo | FAISS encuentra documentos parecidos por significado, pero no permite filtrar directamente por condiciones del negocio. Por ejemplo, no se puede solicitar solamente información de categoría `soporte`, vigente y aplicable a la sucursal `CABA` sin implementar lógica adicional fuera del índice. | ChromaDB permite combinar búsqueda semántica con filtros de metadatos mediante `where`. Así, el sistema puede recuperar documentos similares y, al mismo tiempo, restringir los resultados por `categoria`, `vigente`, `sucursal` u otros campos deterministas. |
| CRUD ineficiente / sin gestión de concurrencia | En FAISS, modificar o eliminar un documento implica administrar manualmente la relación entre posiciones del índice, vectores y el archivo auxiliar de documentos. Esto complica mantener actualizada la base cuando cambian políticas de envío, stock, condiciones de garantía o procesos de devolución. | ChromaDB gestiona los documentos mediante IDs estables y operaciones como `upsert`, `update` y `delete`. Esto permite incorporar, modificar o eliminar conocimiento sin reconstruir manualmente el mapeo entre vectores y documentos. |

En conclusión, FAISS fue útil para comprender cómo se construye y persiste un índice vectorial. Sin embargo, ChromaDB resulta más adecuado para una aplicación de negocio como TecnoSupply Argentina, porque organiza los documentos junto con sus metadatos, permite actualizaciones más simples y habilita búsquedas híbridas.

## B.3 — Evento de negocio en caliente

Se simuló un cambio real de negocio: la notebook Lenovo ThinkPad E14 pasó a estar temporalmente sin stock. Se actualizó el documento `DOC-011` mediante `coleccion.upsert()` y luego se verificó el cambio con:

```python
coleccion.get(ids=["DOC-011"])
```

La verificación devolvió la nueva descripción semántica, junto con los metadatos actualizados de categoría, vigencia, sucursal y tags regionales.

Se utilizó `upsert` porque permite crear el documento si no existe o actualizarlo si ya existe, manteniendo el mismo identificador. No se utilizó `add` porque produciría un error ante un ID existente, ni `update` porque solo funciona cuando se tiene certeza de que el documento ya fue creado.

## B.4 — CLI de búsqueda híbrida

Se desarrolló el script `busqueda_hibrida.py`, que implementa una búsqueda híbrida sobre la colección persistente `conocimiento_tecnosupply`.

La función principal recibe una consulta semántica y filtros opcionales de negocio:

```python
buscar_tecnosupply(
    query_semantica,
    categoria=None,
    sucursal=None,
    solo_activos=True,
    n_resultados=3,
)
```

La consulta se transforma en un embedding mediante `gemini-embedding-001` y se envía a ChromaDB junto con un filtro duro construido mediante `where`. Los filtros se aplican dentro de la operación `collection.query()`, por lo que no se recuperan documentos que debían descartarse.

Ejemplo del núcleo de la búsqueda:

```python
resultado = coleccion.query(
    query_embeddings=[embedding_consulta],
    where=where,
    n_results=n_resultados,
    include=["documents", "metadatas", "distances"],
)
```

### Prueba realizada

Se ejecutó la siguiente consulta:

```text
Consulta semántica: Mi notebook no enciende y necesito ayuda.
Categoría: soporte
Sucursal: todas
Solo documentos vigentes: sí
Cantidad de resultados: 3
```

El sistema generó el siguiente filtro dentro de ChromaDB:

```python
{
    "$and": [
        {"categoria": {"$eq": "soporte"}},
        {"sucursal": {"$eq": "todas"}},
        {"vigente": {"$eq": True}}
    ]
}
```

El resultado recuperado fue `DOC-010`, correspondiente al procedimiento de soporte para una notebook que no enciende, con una distancia coseno de `0.2313`.

![alt text](B4_Captura.png)

La captura de consola adjunta evidencia que la recuperación combinó correctamente similitud semántica y filtros deterministas, sin realizar post-filtrado manual en Python.

## B.5 — ETL y purga semántica

Para probar el proceso de ETL se creó el archivo `base_conocimiento_sucia.json`, con 18 documentos: los 15 originales de la base y 3 documentos agregados manualmente como casi-duplicados.

También se incorporaron inconsistencias intencionales:

- Colisión de ID: un segundo documento con el identificador `DOC-003`.
- Claves con formatos diferentes: `categoriaProducto`, `categoria_producto`, `category`, `estaVigente`, `activo` y `tagsRegionales`.
- Tipos inconsistentes: valores booleanos representados como texto, como `"true"` y `"Sí"`, y tags almacenados como texto separado por comas en lugar de listas.

El script `etl_purga.py` realizó las siguientes tareas:

1. Normalizó las claves de metadatos hacia el esquema final: `categoria`, `vigente`, `sucursal` y `tags_regionales`.
2. Convirtió valores booleanos textuales a valores booleanos reales.
3. Transformó los tags textuales en listas.
4. Resolvió la colisión del identificador `DOC-003`, renombrando el segundo registro como `DOC-003-ETL-01`.
5. Generó embeddings con Gemini y comparó documentos de la misma categoría mediante distancia coseno.
6. Eliminó documentos cuya distancia coseno fuera menor a `0.08`.

### Resultado de la ejecución

```text
Documentos iniciales: 18
Documentos finales: 15
Umbral de distancia coseno: 0.08
Comparación semántica limitada a documentos de la misma categoría.
```

### Colisión de ID resuelta

```text
Colisión resuelta: DOC-003 pasó a llamarse DOC-003-ETL-01.
```

### Documentos eliminados por purga semántica

| Documento eliminado | Documento conservado | Categoría | Distancia coseno | Motivo |
|---|---|---:|---:|---|
| `DOC-003-ETL-01` | `DOC-003` | envíos | 0.0290 | Ambos describían el procedimiento ante una demora de entrega. |
| `DOC-016` | `DOC-005` | reclamos | 0.0244 | Ambos describían el reclamo y la gestión de devolución por producto dañado. |
| `DOC-017` | `DOC-010` | soporte | 0.0243 | Ambos describían el procedimiento inicial ante una notebook que no enciende. |

El umbral de `0.08` se eligió luego de una prueba inicial con un valor de `0.20`, que resultó demasiado permisivo y agrupaba documentos distintos. El valor final permitió detectar únicamente los casi-duplicados agregados de forma intencional.

Un `SELECT DISTINCT` no habría detectado estos casos porque los documentos tenían IDs, redacciones y metadatos diferentes. `DISTINCT` identifica filas exactamente iguales, mientras que la purga semántica identifica textos que expresan el mismo concepto aunque usen sinónimos, distinta redacción o estructuras de metadatos inconsistentes.

## B.6 — Killer Queries

Se realizaron tres consultas trampa para evaluar recuperación semántica, filtros duros y manejo de consultas fuera del catálogo.

| # | Consulta | Qué pone a prueba | Resultado esperado | Resultado real | ¿Pasó? |
|---:|---|---|---|---|---|
| 1 | “La portátil quedó muerta, ni enchufándola arranca. ¿Me pueden dar una mano?” | Poder semántico: utiliza jerga y no repite expresiones exactas del documento, como “notebook no enciende”. | Recuperar `DOC-010`, correspondiente al procedimiento de soporte para una notebook que no enciende. | Se recuperó `DOC-010` con distancia coseno `0.2521`. | Sí |
| 2 | “Mi notebook no enciende y necesito asistencia técnica”, con filtro `categoria=soporte`, `sucursal=CABA` y `vigente=true`. | El metadato salva el día: sin filtro la similitud semántica encuentra soporte, pero el filtro duro debe bloquear documentos que no cumplen la sucursal solicitada. | No devolver resultados, ya que no existe un documento de soporte específico para la sucursal CABA. | Sin filtro se recuperó `DOC-010` con distancia `0.1939`. Con el filtro híbrido no se devolvieron resultados. | Sí |
| 3 | “Necesito contratar un seguro para mi auto antes de viajar.” | Prueba de estrés: consulta completamente fuera del catálogo de TecnoSupply Argentina. | Responder que no existe información disponible, sin inventar una respuesta ni usar un documento irrelevante. | El resultado más cercano fue `DOC-002`, con distancia `0.4169`, pero fue rechazado por superar el umbral de aceptación `0.40`. Se respondió: “No tengo información disponible sobre seguros para automóviles”. | Sí |

Las pruebas muestran que la base vectorial recupera intención aunque cambie la redacción, que los metadatos restringen los resultados según reglas deterministas y que el sistema puede rechazar consultas ajenas al dominio en lugar de responder con información no relacionada.