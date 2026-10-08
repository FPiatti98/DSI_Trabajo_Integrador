from rag_pipeline import crear_cadena_rag


def main():
    cadena_rag = crear_cadena_rag(k=3)

    pregunta = (
    "La notebook llegó rota y no enciende. Además, la factura tiene "
    "mal cargado el CUIT y necesito cambiar la dirección de entrega "
    "antes de que salga el pedido. ¿Qué debo hacer?"
    )   

    resultado = cadena_rag.invoke(
        {"pregunta": pregunta}
    )

    print("=== Prueba de falla del RAG básico — B.1 ===")
    print(f"\nPregunta:\n{pregunta}")

    print(
    "\nRespuesta esperada:"
    "\n- Indicar cómo iniciar el reclamo por producto dañado."
    "\n- Indicar verificaciones iniciales para una notebook que no enciende."
    "\n- Indicar que la corrección de CUIT requiere revisión administrativa."
    "\n- Indicar que cambiar la dirección depende de que el pedido no haya sido despachado."
    )

    print(f"\nRespuesta del RAG básico:\n{resultado['respuesta']}")

    print("\nFuentes recuperadas:")

    for posicion, documento in enumerate(
        resultado["documentos"],
        start=1,
    ):
        print(f"\n{posicion}. {documento.metadata['id']}")
        print(f"Categoría: {documento.metadata.get('categoria')}")
        print(f"Distancia: {documento.metadata.get('distancia'):.4f}")
        print(f"Fragmento: {documento.page_content}")


if __name__ == "__main__":
    main()