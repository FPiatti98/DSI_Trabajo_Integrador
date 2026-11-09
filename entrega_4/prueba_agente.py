from uuid import uuid4

from agente import consultar_agente

EJECUCION = uuid4().hex[:8]

print("=== MATRIZ DE VALIDACIÓN DEL AGENTE ===\n")

print("ESCENARIO 1 — Retriever de conocimiento")
print("Objetivo: responder una consulta de soporte usando ChromaDB local.\n")

respuesta_1 = consultar_agente(
    "Mi notebook no enciende. ¿Qué puedo verificar antes de llevarla al servicio técnico?",
    f"validacion-retriever-{EJECUCION}",
)
print(f"Respuesta: {respuesta_1}\n")
print("-" * 70)

print("\nESCENARIO 2 — Sensor de pedidos")
print("Objetivo: consultar el estado operativo real de un pedido.\n")

respuesta_2 = consultar_agente(
    "¿Cuál es el estado del pedido PED-1002?",
    f"validacion-sensor-{EJECUCION}",
)
print(f"Respuesta: {respuesta_2}\n")
print("-" * 70)

print("\nESCENARIO 3 — Actuador de reclamos")
print("Objetivo: registrar un reclamo de forma explícita.\n")

respuesta_3 = consultar_agente(
    (
        "Quiero registrar un reclamo para el pedido PED-1004. "
        "La notebook llegó con la pantalla rota y no enciende."
    ),
    f"validacion-actuador-{EJECUCION}",
)
print(f"Respuesta: {respuesta_3}\n")
print("-" * 70)

print("\nESCENARIO 4 — Memoria por thread_id")
print("Objetivo: usar un pedido mencionado en un turno anterior.\n")

thread_memoria = f"validacion-memoria-{EJECUCION}"

respuesta_4a = consultar_agente(
    "¿Cuál es el estado del pedido PED-1003?",
    thread_memoria,
)
print(f"Turno 1: {respuesta_4a}\n")

respuesta_4b = consultar_agente(
    "¿Cuál era el producto de ese pedido?",
    thread_memoria,
)
print(f"Turno 2: {respuesta_4b}\n")
print("-" * 70)

print("\nValidación finalizada.")