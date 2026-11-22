import sqlite3
import tempfile
import unittest
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

from tecnosupply.aplicacion.servicio_operaciones import (
    consultar_pedido,
    crear_reclamo,
)
from tecnosupply.dominio.reglas_reclamos import ErrorReglaNegocio
from tecnosupply.infraestructura import (
    base_operaciones,
    pedidos_sqlite,
    reclamos_sqlite,
)


class OperacionesTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="tecnosupply-sqlite-")
        self.recursos = ExitStack()
        self.addCleanup(self.limpiar_recursos)
        self.ruta_bd = Path(self.temporal.name) / "operaciones.db"

        for modulo in (base_operaciones, pedidos_sqlite, reclamos_sqlite):
            self.recursos.enter_context(
                patch.object(modulo, "RUTA_BD_OPERACIONES", self.ruta_bd)
            )

        base_operaciones.inicializar_base_operaciones()

    def limpiar_recursos(self):
        try:
            self.recursos.close()
        finally:
            self.temporal.cleanup()

    def cantidad_reclamos(self):
        with closing(sqlite3.connect(self.ruta_bd)) as conexion:
            return conexion.execute("SELECT COUNT(*) FROM reclamos").fetchone()[0]

    def test_01_inicializacion_crea_cuatro_pedidos(self):
        with closing(sqlite3.connect(self.ruta_bd)) as conexion:
            cantidad = conexion.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
        self.assertEqual(cantidad, 4)
        self.assertEqual(self.cantidad_reclamos(), 0)

    def test_02_consulta_normaliza_identificador(self):
        pedido = consultar_pedido("  ped-1003  ")
        self.assertEqual(pedido["numero_pedido"], "PED-1003")
        self.assertEqual(pedido["estado"], "en tránsito")
        self.assertEqual(pedido["producto"], "Mouse Logitech MX Master")

    def test_03_consulta_pedido_inexistente(self):
        with self.assertRaises(ErrorReglaNegocio):
            consultar_pedido("PED-9999")

    def test_04_registra_reclamo_y_persiste_datos(self):
        reclamo = crear_reclamo(" ped-1004 ", " La pantalla llegó dañada. ")
        self.assertGreater(reclamo["id_reclamo"], 0)
        self.assertEqual(reclamo["numero_pedido"], "PED-1004")
        self.assertEqual(reclamo["estado"], "abierto")
        self.assertIn("no implica aprobación automática", reclamo["aclaracion"])

        # Una conexion distinta comprueba que la transaccion quedo confirmada.
        with closing(sqlite3.connect(self.ruta_bd)) as conexion:
            fila = conexion.execute(
                "SELECT numero_pedido, descripcion, estado, fecha_creacion "
                "FROM reclamos WHERE id_reclamo = ?",
                (reclamo["id_reclamo"],),
            ).fetchone()
        self.assertEqual(fila[0], "PED-1004")
        self.assertEqual(fila[1], "La pantalla llegó dañada.")
        self.assertEqual(fila[2], "abierto")
        self.assertEqual(fila[3], reclamo["fecha_creacion_utc"])
        self.assertEqual(self.cantidad_reclamos(), 1)

    def test_05_rechaza_descripcion_breve_sin_insertar(self):
        with self.assertRaises(ErrorReglaNegocio):
            crear_reclamo("PED-1004", "roto")
        self.assertEqual(self.cantidad_reclamos(), 0)

    def test_06_rechaza_pedido_vacio_sin_insertar(self):
        with self.assertRaises(ErrorReglaNegocio):
            crear_reclamo("   ", "La pantalla llegó dañada.")
        self.assertEqual(self.cantidad_reclamos(), 0)

    def test_07_rechaza_reclamo_de_pedido_inexistente(self):
        with self.assertRaises(ErrorReglaNegocio):
            crear_reclamo("PED-9999", "La pantalla llegó dañada.")
        self.assertEqual(self.cantidad_reclamos(), 0)

    def test_08_sqlite_impide_reclamos_sin_pedido_asociado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            reclamos_sqlite.insertar_reclamo(
                "PED-9999", "La pantalla llegó dañada.", "abierto"
            )
        self.assertEqual(self.cantidad_reclamos(), 0)

    def test_09_reinicializar_conserva_datos_y_no_duplica(self):
        reclamo = crear_reclamo("PED-1004", "La pantalla llegó dañada.")
        with closing(sqlite3.connect(self.ruta_bd)) as conexion:
            with conexion:
                conexion.execute(
                    "UPDATE pedidos SET estado = ? WHERE numero_pedido = ?",
                    ("entregado", "PED-1003"),
                )

        base_operaciones.inicializar_base_operaciones()
        self.assertEqual(consultar_pedido("PED-1003")["estado"], "entregado")
        self.assertEqual(self.cantidad_reclamos(), 1)
        with closing(sqlite3.connect(self.ruta_bd)) as conexion:
            self.assertEqual(
                conexion.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 4
            )
            self.assertIsNotNone(
                conexion.execute(
                    "SELECT id_reclamo FROM reclamos WHERE id_reclamo = ?",
                    (reclamo["id_reclamo"],),
                ).fetchone()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
