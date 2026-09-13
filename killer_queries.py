from vector_db import buscar_tecnosupply


UMBRAL_RECHAZO = 0.40


def primer_resultado(resultado):
    if not resultado["ids"][0]:
        return None

    return {
        "id": resultado["ids"][0][0],
        "distancia": resultado["distances"][0][0],
        "documento": resultado["documents"][0][0],
    }


def prueba_1_jerga():
    print("\n" + "=" * 70)
    print("KILLER QUERY 1 — Jerga sin palabras exactas")

    resultado, _ = buscar_tecnosupply(
        query_semantica=(
            "La portátil quedó muerta, ni enchufándola arranca. "
            "¿Me pueden dar una mano?"
        ),
        categoria="soporte",
        sucursal="todas",
        solo_activos=True,
        n_resultados=1,
    )

    dato = primer_resultado(resultado)

    if dato:
        print(f"Resultado: {dato['id']}")
        print(f"Distancia: {dato['distancia']:.4f}")
        print(f"Documento: {dato['documento']}")
    else:
        print("Resultado: no se encontró información.")


def prueba_2_filtro_duro():
    print("\n" + "=" * 70)
    print("KILLER QUERY 2 — El filtro duro bloquea un resultado semántico")

    consulta = "Mi notebook no enciende y necesito asistencia técnica."

    resultado_crudo, _ = buscar_tecnosupply(
        query_semantica=consulta,
        solo_activos=True,
        n_resultados=1,
    )

    dato_crudo = primer_resultado(resultado_crudo)

    print("Búsqueda semántica sin filtro:")
    if dato_crudo:
        print(f"Resultado: {dato_crudo['id']}")
        print(f"Distancia: {dato_crudo['distancia']:.4f}")

    resultado_hibrido, where = buscar_tecnosupply(
        query_semantica=consulta,
        categoria="soporte",
        sucursal="CABA",
        solo_activos=True,
        n_resultados=1,
    )

    dato_hibrido = primer_resultado(resultado_hibrido)

    print(f"\nFiltro aplicado: {where}")

    if dato_hibrido:
        print(f"Resultado híbrido: {dato_hibrido['id']}")
        print(f"Distancia: {dato_hibrido['distancia']:.4f}")
    else:
        print(
            "Resultado híbrido: no existe un documento de soporte "
            "específico para la sucursal CABA."
        )


def prueba_3_fuera_catalogo():
    print("\n" + "=" * 70)
    print("KILLER QUERY 3 — Consulta fuera del catálogo")

    resultado, _ = buscar_tecnosupply(
        query_semantica=(
            "Necesito contratar un seguro para mi auto antes de viajar."
        ),
        solo_activos=True,
        n_resultados=1,
    )

    dato = primer_resultado(resultado)

    if not dato or dato["distancia"] > UMBRAL_RECHAZO:
        print(
            "Respuesta segura: No tengo información disponible "
            "sobre seguros para automóviles."
        )

        if dato:
            print(
                f"El resultado más cercano fue {dato['id']} "
                f"con distancia {dato['distancia']:.4f}, "
                "pero fue rechazado por superar el umbral."
            )
    else:
        print(f"Resultado inesperadamente aceptado: {dato['id']}")
        print(f"Distancia: {dato['distancia']:.4f}")


def main():
    print("=== Killer Queries — TecnoSupply Argentina ===")

    prueba_1_jerga()
    prueba_2_filtro_duro()
    prueba_3_fuera_catalogo()


if __name__ == "__main__":
    main()