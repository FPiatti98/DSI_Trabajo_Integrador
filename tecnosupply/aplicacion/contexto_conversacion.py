"""Resuelve referencias de lectura usando únicamente el historial del hilo."""

import re
from collections.abc import Iterable


PATRON_PEDIDO = re.compile(r"\bPED-\d+\b", re.IGNORECASE)


def resolver_referencia_pedido(
    consulta: str,
    consultas_previas: Iterable[str],
) -> str:
    """Aclara qué pedido corresponde a una pregunta de producto o estado.

    Usa la mención más reciente del usuario en el mismo hilo. Si esa mención
    contiene varios pedidos, no elige uno. No modifica solicitudes de acciones
    ni preguntas generales de soporte, facturación o reclamos.
    """
    if PATRON_PEDIDO.search(consulta):
        return consulta

    referencia = re.search(
        r"\b(?:ese|este|aquel|dicho|el mismo)\s+pedido\b",
        consulta,
        re.IGNORECASE,
    )
    dato_operativo = re.search(
        r"\b(?:producto|estado|art[ií]culo)\b", consulta, re.IGNORECASE
    )
    otro_tema = re.search(
        r"\b(?:registr\w*|crea\w*|reclam\w*|cancel\w*|devol\w*|"
        r"reintegr\w*|dañ\w*|rot[oa]s?|factur\w*|cuit|direcci[oó]n|"
        r"cambi\w*|modific\w*)\b",
        consulta,
        re.IGNORECASE,
    )
    if not referencia or not dato_operativo or otro_tema:
        return consulta

    for previa in reversed(list(consultas_previas)):
        pedidos = {pedido.upper() for pedido in PATRON_PEDIDO.findall(previa)}
        if not pedidos:
            continue
        if len(pedidos) != 1:
            return consulta

        pedido = pedidos.pop()
        return f"{consulta}\nPedido referido en esta conversación: {pedido}."

    return consulta
