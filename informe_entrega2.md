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