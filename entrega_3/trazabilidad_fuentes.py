from rag_pipeline import crear_cadena_rag


CONSULTAS = [
    "¿Cómo puedo solicitar una copia de la factura de mi compra?",
    "El producto llegó roto y quiero solicitar una devolución. ¿Qué debo hacer?",
]


def main():
    cadena_rag = crear_cadena_rag(k=3)

    print("=== Trazabilidad de fuentes A.4 ===")

    for indice, pregunta in enumerate(CONSULTAS, start=1):
        resultado = cadena_rag.invoke(
            {"pregunta": pregunta}
        )

        print("\n" + "=" * 70)
        print(f"CONSULTA {indice}")
        print(f"\nPregunta: {pregunta}")
        print(f"\nRespuesta: {resultado['respuesta']}")
        print("\nDocumentos utilizados como fuente:")

        for posicion, documento in enumerate(
            resultado["documentos"],
            start=1,
        ):
            print(f"\n{posicion}. ID: {documento.metadata['id']}")
            print(
                f"Categoría: {documento.metadata.get('categoria')}"
            )
            print(
                f"Sucursal: {documento.metadata.get('sucursal')}"
            )
            print(
                f"Vigente: {documento.metadata.get('vigente')}"
            )
            print(
                f"Distancia: {documento.metadata.get('distancia'):.4f}"
            )
            print(f"Fragmento: {documento.page_content}")


if __name__ == "__main__":
    main()