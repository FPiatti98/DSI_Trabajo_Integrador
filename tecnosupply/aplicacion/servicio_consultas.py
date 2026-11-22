from time import perf_counter
from typing import Any

from tecnosupply.aplicacion.agente import (
    consultar_agente_detallado,
    obtener_historial,
)
from tecnosupply.aplicacion.seguridad import (
    ErrorSeguridad,
    enmascarar_datos_personales,
    validar_entrada,
)
from tecnosupply.config import (
    MODELO_OLLAMA,
    RUTA_BD_OPERACIONES,
    RUTA_CHROMA_OLLAMA,
    RUTA_MEMORIA,
)
from tecnosupply.infraestructura.observabilidad import (
    obtener_metricas,
    registrar_consulta,
)


def procesar_consulta(consulta: str, thread_id: str) -> dict[str, Any]:
    """
    Coordina seguridad, agente, proteccion de salida y observabilidad.

    Devuelve datos de aplicacion, sin construir respuestas HTTP.
    Los errores se propagan para que presentacion decida su codigo HTTP.
    """
    inicio = perf_counter()
    estado = "error"
    bloqueado = False
    herramientas: list[str] = []
    detalle_error: str | None = None
    consulta_validada = consulta

    try:
        consulta_validada = validar_entrada(consulta)

        resultado = consultar_agente_detallado(
            consulta=consulta_validada,
            thread_id=thread_id,
        )

        respuesta_segura = enmascarar_datos_personales(
            str(resultado["respuesta"])
        )
        herramientas = resultado["herramientas"]
        estado = "ok"

        return {
            "thread_id": thread_id,
            "respuesta": respuesta_segura,
            "herramientas_usadas": herramientas,
        }

    except ErrorSeguridad as error:
        estado = "bloqueado"
        bloqueado = True
        detalle_error = str(error)
        raise

    except ValueError as error:
        detalle_error = str(error)
        raise

    except Exception as error:
        detalle_error = type(error).__name__
        raise

    finally:
        registrar_consulta(
            thread_id=thread_id,
            consulta=consulta_validada if estado == "ok" else consulta,
            latencia_ms=(perf_counter() - inicio) * 1000,
            estado=estado,
            herramientas=herramientas,
            bloqueado=bloqueado,
            detalle_error=detalle_error,
        )


def recuperar_historial(thread_id: str) -> dict[str, Any]:
    """Recupera y protege el historial visible de una conversacion."""
    historial_original = obtener_historial(thread_id)

    historial_seguro = [
        {
            "rol": mensaje["rol"],
            "contenido": enmascarar_datos_personales(mensaje["contenido"]),
        }
        for mensaje in historial_original
    ]

    return {
        "thread_id": thread_id,
        "cantidad_mensajes": len(historial_seguro),
        "historial": historial_seguro,
    }


def consultar_salud() -> dict[str, str | bool]:
    """Informa la configuracion y existencia de los recursos locales."""
    return {
        "estado": "ok",
        "modelo": MODELO_OLLAMA,
        "memoria_sqlite": RUTA_MEMORIA.exists(),
        "base_operaciones": RUTA_BD_OPERACIONES.exists(),
        "chroma_local": RUTA_CHROMA_OLLAMA.exists(),
        "seguridad_activa": True,
    }


def consultar_metricas() -> dict[str, Any]:
    """Solicita las metricas operativas persistidas."""
    return obtener_metricas()
