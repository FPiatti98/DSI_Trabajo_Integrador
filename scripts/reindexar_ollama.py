"""Genera la base vectorial local desde la raíz del repositorio.

Uso: python -m scripts.reindexar_ollama
"""

from tecnosupply.infraestructura.indexacion_chroma import reindexar_conocimiento


def main() -> None:
    """Ejecuta la reindexación usando la configuración central del proyecto."""
    reindexar_conocimiento()


if __name__ == "__main__":
    main()
