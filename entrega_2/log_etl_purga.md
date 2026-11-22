# Log de ETL y purga semántica

- Documentos iniciales: 18
- Documentos finales: 15
- Umbral de distancia coseno: 0.08
- Comparación semántica limitada a documentos de la misma categoría.

## Colisiones de IDs resueltas
- Colisión resuelta: `DOC-003` pasó a llamarse `DOC-003-ETL-01`.

## Documentos eliminados por purga semántica
- Se eliminó `DOC-003-ETL-01` por ser casi-duplicado de `DOC-003` en la categoría `envios` (distancia coseno: `0.0290`).
- Se eliminó `DOC-016` por ser casi-duplicado de `DOC-005` en la categoría `reclamos` (distancia coseno: `0.0244`).
- Se eliminó `DOC-017` por ser casi-duplicado de `DOC-010` en la categoría `soporte` (distancia coseno: `0.0243`).