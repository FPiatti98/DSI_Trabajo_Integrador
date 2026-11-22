import faiss

from pipeline_vectorial import (
    cargar_base,
    crear_cliente,
    generar_embeddings_documentos,
)


def main():
    documentos, _ = cargar_base()
    client = crear_cliente()

    print("Generando embeddings y construyendo el índice solamente en RAM...")

    embeddings = generar_embeddings_documentos(client, documentos)
    faiss.normalize_L2(embeddings)

    indice = faiss.IndexFlatL2(embeddings.shape[1])
    indice.add(embeddings)

    print(f"Índice creado en RAM con {indice.ntotal} documentos.")
    print("No se ejecutó faiss.write_index().")
    print("Al finalizar este programa, el índice se perderá.")


if __name__ == "__main__":
    main()