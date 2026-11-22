from typing import Any

from tecnosupply.infraestructura.conocimiento_chroma import (
    buscar_documentos,
)


def consultar_conocimiento(consulta: str) -> dict[str, Any]:
    """
    Coordina la búsqueda de conocimiento para atender una consulta.

    Valida el texto y solicita hasta tres documentos vigentes.
    Devuelve los resultados sin redactar la respuesta final.
    """
    consulta_limpia = consulta.strip()

    if not consulta_limpia:
        raise ValueError(
            "La consulta para la base de conocimiento está vacía."
        )

    documentos = buscar_documentos(
        consulta=consulta_limpia,
        n_resultados=3,
        filtros={"vigente": {"$eq": True}},
    )

    return {
        "consulta": consulta_limpia,
        "cantidad_resultados": len(documentos),
        "resultados": documentos,
    }