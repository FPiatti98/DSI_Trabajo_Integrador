from __future__ import annotations

import re


class ErrorSeguridad(ValueError):
    """Error controlado cuando un guardrail bloquea una consulta."""


MAXIMO_CARACTERES_CONSULTA = 1000

PATRONES_INYECCION = [
    r"\bignor[aá]s+(todas?\s+)?las?\s+instrucciones\b",
    r"\bignor[eé]s+(todas?\s+)?las?\s+instrucciones\b",
    r"\bomit[ií](?:r[eé])?\s+(todas?\s+)?las?\s+reglas\b",
    r"\bact[uú][aá]\s+como\b",
    r"\bsystem\s+prompt\b",
    r"\bprompt\s+del\s+sistema\b",
    r"\brevel[aá]s+(el\s+)?prompt\b",
    r"\bjailbreak\b",
    r"\bDAN\b",
    r"\bbypass\b",
]


def validar_longitud(consulta: str) -> None:
    """Bloquea consultas vacías o excesivamente largas."""
    if not consulta or not consulta.strip():
        raise ErrorSeguridad("La consulta no puede estar vacía.")

    if len(consulta) > MAXIMO_CARACTERES_CONSULTA:
        raise ErrorSeguridad(
            f"La consulta supera el límite de "
            f"{MAXIMO_CARACTERES_CONSULTA} caracteres."
        )


def validar_prompt_injection(consulta: str) -> None:
    """Detecta patrones frecuentes de prompt injection."""
    for patron in PATRONES_INYECCION:
        if re.search(patron, consulta, flags=re.IGNORECASE):
            raise ErrorSeguridad(
                "La consulta fue bloqueada por una política de seguridad."
            )


def validar_entrada(consulta: str) -> str:
    """Ejecuta todos los validadores de entrada."""
    consulta_limpia = consulta.strip()
    validar_longitud(consulta_limpia)
    validar_prompt_injection(consulta_limpia)
    return consulta_limpia


def enmascarar_datos_personales(texto: str) -> str:
    """
    Oculta emails, DNI, CUIT y teléfonos etiquetados en la respuesta final.
    """
    texto_protegido = texto

    texto_protegido = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[EMAIL_OCULTO]",
        texto_protegido,
    )

    texto_protegido = re.sub(
        r"(?i)\bDNI\s*[:#-]?\s*\d{7,8}\b",
        "DNI: [DNI_OCULTO]",
        texto_protegido,
    )

    texto_protegido = re.sub(
        r"(?i)\bCUIT\s*[:#-]?\s*\d{2}-?\d{8}-?\d\b",
        "CUIT: [CUIT_OCULTO]",
        texto_protegido,
    )

    texto_protegido = re.sub(
        r"(?i)\b(?:tel[eé]fono|tel|celular|cel)\s*[:#-]?\s*"
        r"(?:\+?54\s?)?(?:\d{2,4}[\s-]?)?\d{3,4}[-\s]?\d{4}\b",
        "TELÉFONO: [TELÉFONO_OCULTO]",
        texto_protegido,
    )

    return texto_protegido