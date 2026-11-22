"""Ejecuta las pruebas de seguridad: python -m scripts.security_tests."""

import unittest
from pathlib import Path


def main() -> int:
    """Carga la suite de seguridad y devuelve un código de salida verificable."""
    carpeta_tests = Path(__file__).resolve().parents[1] / "tests"
    archivo_suite = carpeta_tests / "test_seguridad.py"
    if not archivo_suite.is_file():
        raise FileNotFoundError(f"No se encontró la suite de seguridad: {archivo_suite}")

    suite = unittest.defaultTestLoader.discover(
        start_dir=str(carpeta_tests),
        pattern="test_seguridad.py",
    )
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
