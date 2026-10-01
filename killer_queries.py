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


def prueba_2_filtro_vigencia():
    print("\n" + "=" * 70)
    print("KILLER QUERY 2 — El filtro de vigencia bloquea una política vencida")

    consulta = (
        "¿Mi notebook llega dentro de 24 horas? "
        "Necesito una entrega express."
    )

    resultado_sin_filtro, where_sin_filtro = buscar_tecnosupply(
        query_semantica=consulta,
        categoria="envios",
        sucursal="CABA",
        solo_activos=False,
        n_resultados=1,
    )

    dato_sin_filtro = primer_resultado(resultado_sin_filtro)

    print("Búsqueda sin filtro de vigencia:")
    print(f"Filtro aplicado: {where_sin_filtro}")

    if dato_sin_filtro:
        print(f"Resultado: {dato_sin_filtro['id']}")
        print(f"Distancia: {dato_sin_filtro['distancia']:.4f}")
        print(f"Documento: {dato_sin_filtro['documento']}")

    resultado_hibrido, where_hibrido = buscar_tecnosupply(
        query_semantica=consulta,
        categoria="envios",
        sucursal="CABA",
        solo_activos=True,
        n_resultados=1,
    )

    dato_hibrido = primer_resultado(resultado_hibrido)

    print("\nBúsqueda híbrida con solo documentos vigentes:")
    print(f"Filtro aplicado: {where_hibrido}")

    if dato_hibrido:
        print(f"Resultado híbrido: {dato_hibrido['id']}")
        print(f"Distancia: {dato_hibrido['distancia']:.4f}")
        print(f"Documento: {dato_hibrido['documento']}")
    else:
        print("Resultado híbrido: no se encontró información.")


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
    prueba_2_filtro_vigencia()
    prueba_3_fuera_catalogo()


if __name__ == "__main__":
    main()