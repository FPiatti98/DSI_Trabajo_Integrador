# Matriz de validación del agente

| Escenario | Herramienta o capacidad evaluada | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| 1. Consulta de soporte | `buscar_conocimiento` | Recuperar información vigente sobre una notebook que no enciende, sin inventar pasos. | Recuperó `DOC-010` y respondió únicamente con la verificación de cargador, conexión eléctrica e indicadores luminosos. | Correcto |
| 2. Estado de pedido | `consultar_estado_pedido` | Consultar el estado real del pedido `PED-1002`. | Informó que `PED-1002` está despachado, corresponde a un monitor Samsung de 24 pulgadas y mostró la fecha de actualización. | Correcto |
| 3. Registro de reclamo | `registrar_reclamo` | Registrar un reclamo explícito asociado a `PED-1004`. | Registró el reclamo con identificador `4`, estado `abierto` y aclaró que no implica devolución, reemplazo ni reintegro automático. | Correcto |
| 4. Memoria conversacional | Memoria SQLite por `thread_id` | Recordar el pedido mencionado en el primer turno y resolver una referencia posterior. | Tras consultar `PED-1003`, respondió correctamente que el producto era un Mouse Logitech MX Master cuando se preguntó por “ese pedido”. | Correcto |