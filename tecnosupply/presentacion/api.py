from fastapi import APIRouter, HTTPException

from tecnosupply.aplicacion.seguridad import ErrorSeguridad
from tecnosupply.aplicacion.servicio_consultas import (
    consultar_metricas,
    consultar_salud,
    procesar_consulta,
    recuperar_historial,
)
from tecnosupply.presentacion.schemas import (
    ConsultaRequest,
    ConsultaResponse,
    EstadoResponse,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | bool]:
    """Devuelve la informacion de los recursos locales del sistema."""
    return consultar_salud()


@router.post("/consultar", response_model=ConsultaResponse)
def consultar(datos: ConsultaRequest) -> ConsultaResponse:
    """Recibe la solicitud HTTP y delega su procesamiento a aplicacion."""
    try:
        resultado = procesar_consulta(
            consulta=datos.consulta,
            thread_id=datos.thread_id,
        )
        return ConsultaResponse(**resultado)

    except ErrorSeguridad as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="No fue posible procesar la consulta del agente.",
        ) from error


@router.get("/estado/{thread_id}", response_model=EstadoResponse)
def estado(thread_id: str) -> EstadoResponse:
    """Devuelve el historial protegido de una conversacion."""
    try:
        return EstadoResponse(**recuperar_historial(thread_id))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="No fue posible recuperar el estado de la conversación.",
        ) from error


@router.get("/metricas")
def metricas() -> dict:
    """Devuelve las metricas operativas acumuladas."""
    return consultar_metricas()
