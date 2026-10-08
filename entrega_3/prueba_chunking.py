from rag_pipeline import crear_cadena_rag


COLECCION_CHUNKS = "conocimiento_tecnosupply_chunks"


def main():
    cadena_rag = crear_cadena_rag(
        k=3,
        collection_name=COLECCION_CHUNKS,
    )

    pregunta = (
        "La notebook llegó rota y no enciende. Además, la factura tiene "
        "mal cargado el CUIT y necesito cambiar la dirección de entrega "
        "antes de que salga el pedido. ¿Qué debo hacer?"
    )

    resultado = cadena_rag.invoke(
        {"pregunta": pregunta}
    )

    print("=== Prueba de chunking B.2 ===")
    print(f"\nPregunta:\n{pregunta}")
    print(f"\nRespuesta con chunks:\n{resultado['respuesta']}")
    print("\nChunks recuperados:")

    for posicion, documento in enumerate(
        resultado["documentos"],
        start=1,
    ):
        print(f"\n{posicion}. {documento.metadata['id']}")
        print(
            f"Documento original: "
            f"{documento.metadata.get('document_id')}"
        )
        print(f"Chunk: {documento.metadata.get('chunk_index')}")
        print(f"Categoría: {documento.metadata.get('categoria')}")
        print(f"Distancia: {documento.metadata.get('distancia'):.4f}")
        print(f"Fragmento: {documento.page_content}")


if __name__ == "__main__":
    main()