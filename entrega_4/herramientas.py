from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings

CARPETA_ENTREGA_4 = Path(__file__).resolve().parent

RUTA_BD_OPERACIONES = CARPETA_ENTREGA_4 / "operaciones.db"
RUTA_CHROMA_OLLAMA = CARPETA_ENTREGA_4 / "chroma_ollama"

NOMBRE_COLECCION = "conocimiento_tecnosupply_ollama"
MODELO_EMBEDDINGS = "nomic-embed-text"
URL_OLLAMA = "http://localhost:11434"


def obtener_conexion() -> sqlite3.Connection:
    """Abre una conexión SQLite con claves foráneas habilitadas."""
    conexion = sqlite3.connect(RUTA_BD_OPERACIONES)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def inicializar_base_operaciones() -> None:
    """
    Crea la base SQLite local con pedidos ficticios para la demostración.

    La base representa un sistema operativo externo al RAG. El agente la usa
    mediante herramientas, sin acceder directamente a SQL durante la conversación.
    """
    with obtener_conexion() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                numero_pedido TEXT PRIMARY KEY,
                estado TEXT NOT NULL,
                producto TEXT NOT NULL,
                fecha_actualizacion TEXT NOT NULL
            )
            """
        )

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS reclamos (
                id_reclamo INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_pedido TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                estado TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                FOREIGN KEY (numero_pedido) REFERENCES pedidos(numero_pedido)
            )
            """
        )

        pedidos_iniciales = [
            (
                "PED-1001",
                "confirmado",
                "Notebook Lenovo ThinkPad E14",
                "2026-11-01 10:30",
            ),
            (
                "PED-1002",
                "despachado",
                "Monitor Samsung 24 pulgadas",
                "2026-11-02 14:15",
            ),
            (
                "PED-1003",
                "en tránsito",
                "Mouse Logitech MX Master",
                "2026-11-03 09:40",
            ),
            (
                "PED-1004",
                "entregado",
                "Notebook ASUS Vivobook",
                "2026-11-04 16:20",
            ),
        ]

        conexion.executemany(
            """
            INSERT OR IGNORE INTO pedidos (
                numero_pedido,
                estado,
                producto,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?)
            """,
            pedidos_iniciales,
        )


def obtener_coleccion_local():
    """
    Abre la colección ChromaDB creada con embeddings locales de Ollama.

    Raises:
        FileNotFoundError: Si todavía no se ejecutó reindexar_ollama.py.
    """
    if not RUTA_CHROMA_OLLAMA.exists():
        raise FileNotFoundError(
            "No existe la colección local. Ejecutá primero "
            "`python entrega_4/reindexar_ollama.py`."
        )

    cliente = chromadb.PersistentClient(path=str(RUTA_CHROMA_OLLAMA))
    return cliente.get_collection(name=NOMBRE_COLECCION)


@tool
def buscar_conocimiento(consulta: str) -> str:
    """
    Busca información vigente en la base de conocimiento de TecnoSupply.

    Usa la base de conocimiento de la Entrega 3 reindexada en ChromaDB con
    embeddings locales `nomic-embed-text` de Ollama. Debe utilizarse para
    responder consultas generales sobre soporte, facturación, envíos, stock,
    pagos, garantías o reclamos.

    Args:
        consulta: Pregunta del usuario expresada en lenguaje natural.

    Returns:
        Un JSON con hasta tres documentos vigentes relevantes, sus
        identificadores, categorías, distancia semántica y contenido.

    Safety:
        Esta herramienta solo consulta información. No modifica pedidos,
        reclamos, facturas ni stock.
    """
    consulta = consulta.strip()

    if not consulta:
        return json.dumps(
            {"error": "La consulta para la base de conocimiento está vacía."},
            ensure_ascii=False,
        )

    try:
        coleccion = obtener_coleccion_local()

        embeddings = OllamaEmbeddings(
            model=MODELO_EMBEDDINGS,
            base_url=URL_OLLAMA,
        )

        embedding_consulta = embeddings.embed_query(consulta)

        resultado = coleccion.query(
            query_embeddings=[embedding_consulta],
            n_results=3,
            where={"vigente": {"$eq": True}},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as error:
        return json.dumps(
            {
                "error": "No fue posible consultar la base de conocimiento local.",
                "detalle": str(error),
            },
            ensure_ascii=False,
        )

    ids = resultado.get("ids", [[]])[0]
    documentos = resultado.get("documents", [[]])[0]
    metadatos_lista = resultado.get("metadatas", [[]])[0]
    distancias = resultado.get("distances", [[]])[0]

    resultados = []

    for identificador, documento, metadatos, distancia in zip(
        ids,
        documentos,
        metadatos_lista,
        distancias,
    ):
        metadatos = metadatos or {}

        resultados.append(
            {
                "id": identificador,
                "categoria": metadatos.get("categoria", "N/D"),
                "sucursal": metadatos.get("sucursal", "N/D"),
                "vigente": metadatos.get("vigente", "N/D"),
                "distancia": round(float(distancia), 4),
                "contenido": documento,
            }
        )

    return json.dumps(
        {
            "consulta": consulta,
            "cantidad_resultados": len(resultados),
            "resultados": resultados,
        },
        ensure_ascii=False,
    )


@tool
def consultar_estado_pedido(numero_pedido: str) -> str:
    """
    Consulta el estado operativo actual de un pedido de TecnoSupply.

    Funciona como sensor del dominio: obtiene información de solo lectura
    desde la base de operaciones SQLite. Debe utilizarse cuando el usuario
    aporte un número de pedido y solicite conocer su estado logístico.

    Args:
        numero_pedido: Identificador del pedido, por ejemplo `PED-1001`.

    Returns:
        Un JSON con el número de pedido, estado actual, producto y fecha de
        última actualización. Si el pedido no existe, informa el error.

    Safety:
        Esta herramienta no modifica datos. Solo informa el estado disponible
        en el sistema de operaciones simulado.
    """
    inicializar_base_operaciones()
    numero_pedido = numero_pedido.strip().upper()

    if not numero_pedido:
        return json.dumps(
            {"error": "Debe indicar un número de pedido."},
            ensure_ascii=False,
        )

    with obtener_conexion() as conexion:
        pedido = conexion.execute(
            """
            SELECT numero_pedido, estado, producto, fecha_actualizacion
            FROM pedidos
            WHERE numero_pedido = ?
            """,
            (numero_pedido,),
        ).fetchone()

    if pedido is None:
        return json.dumps(
            {
                "error": f"No se encontró el pedido {numero_pedido}.",
                "sugerencia": "Verifique el formato. Ejemplo válido: PED-1001.",
            },
            ensure_ascii=False,
        )

    return json.dumps(dict(pedido), ensure_ascii=False)


@tool
def registrar_reclamo(numero_pedido: str, descripcion: str) -> str:
    """
    Registra un reclamo de postventa asociado a un pedido existente.

    Funciona como actuador del dominio: crea un registro persistente en SQLite
    para que el área de Postventa lo gestione. Debe usarse únicamente cuando
    el usuario confirme que desea iniciar un reclamo y proporcione una
    descripción suficiente del inconveniente.

    Args:
        numero_pedido: Identificador del pedido afectado, por ejemplo `PED-1001`.
        descripcion: Descripción concreta del problema informado por el cliente.

    Returns:
        Un JSON con el identificador del reclamo, el pedido asociado, estado
        inicial `abierto` y fecha de creación. Si el pedido no existe o la
        descripción es insuficiente, devuelve un error.

    Safety:
        Esta herramienta registra una solicitud, pero no autoriza devoluciones,
        reemplazos ni reintegros. Esas decisiones requieren validación humana
        y verificación de las condiciones comerciales.
    """
    inicializar_base_operaciones()

    numero_pedido = numero_pedido.strip().upper()
    descripcion = descripcion.strip()

    if not numero_pedido:
        return json.dumps(
            {"error": "Debe indicar el número de pedido para registrar el reclamo."},
            ensure_ascii=False,
        )

    if len(descripcion) < 10:
        return json.dumps(
            {
                "error": (
                    "La descripción es demasiado breve. "
                    "Indique qué producto presenta el problema y qué ocurrió."
                )
            },
            ensure_ascii=False,
        )

    with obtener_conexion() as conexion:
        pedido = conexion.execute(
            """
            SELECT numero_pedido
            FROM pedidos
            WHERE numero_pedido = ?
            """,
            (numero_pedido,),
        ).fetchone()

        if pedido is None:
            return json.dumps(
                {
                    "error": (
                        f"No se puede registrar el reclamo porque "
                        f"el pedido {numero_pedido} no existe."
                    )
                },
                ensure_ascii=False,
            )

        fecha_creacion = datetime.now(timezone.utc).isoformat()

        cursor = conexion.execute(
            """
            INSERT INTO reclamos (
                numero_pedido,
                descripcion,
                estado,
                fecha_creacion
            )
            VALUES (?, ?, 'abierto', ?)
            """,
            (numero_pedido, descripcion, fecha_creacion),
        )

    return json.dumps(
        {
            "mensaje": "Reclamo registrado correctamente.",
            "id_reclamo": cursor.lastrowid,
            "numero_pedido": numero_pedido,
            "estado": "abierto",
            "fecha_creacion_utc": fecha_creacion,
            "aclaracion": (
                "El registro no implica aprobación automática de devolución, "
                "reemplazo ni reintegro."
            ),
        },
        ensure_ascii=False,
    )


HERRAMIENTAS = [
    buscar_conocimiento,
    consultar_estado_pedido,
    registrar_reclamo,
]


if __name__ == "__main__":
    inicializar_base_operaciones()

    print("Herramientas disponibles:")
    for herramienta in HERRAMIENTAS:
        print(f"- {herramienta.name}: {herramienta.description.splitlines()[0]}")