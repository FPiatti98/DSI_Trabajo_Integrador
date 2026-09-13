# Resultados de Killer Queries — B.6

| # | Consulta | Qué pone a prueba | Resultado esperado | Resultado real | ¿Pasó? |
|---:|---|---|---|---|---|
| 1 | “La portátil quedó muerta, ni enchufándola arranca. ¿Me pueden dar una mano?” | Poder semántico con jerga y sin coincidencias literales con el documento. | Recuperar el procedimiento de soporte para una notebook que no enciende. | Se recuperó `DOC-010`, correspondiente al procedimiento de soporte, con distancia coseno `0.2521`. | Sí |
| 2 | “Mi notebook no enciende y necesito asistencia técnica”, con filtros `categoria=soporte`, `sucursal=CABA` y `vigente=true`. | Que el filtro duro bloquee resultados semánticamente similares que no cumplen los metadatos requeridos. | No devolver resultados si no hay un documento de soporte específico para CABA. | Sin filtros se recuperó `DOC-010` con distancia `0.1939`. Con el filtro híbrido no se devolvieron resultados. | Sí |
| 3 | “Necesito contratar un seguro para mi auto antes de viajar.” | Consulta fuera del catálogo y aplicación del umbral de aceptación. | Responder que no hay información disponible, sin utilizar un documento irrelevante. | El resultado más cercano fue `DOC-002`, con distancia `0.4169`. Como superó el umbral de `0.40`, fue rechazado y el sistema respondió que no posee información sobre seguros para automóviles. | Sí |

## Conclusión

Las pruebas verifican que la búsqueda semántica comprende expresiones coloquiales, que los filtros de metadatos se aplican dentro de ChromaDB y que el sistema rechaza consultas ajenas al dominio en lugar de alucinar una respuesta.