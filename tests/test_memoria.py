import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tecnosupply.aplicacion.contexto_conversacion import resolver_referencia_pedido


class ContextoConversacionTests(unittest.TestCase):
    def test_01_resuelve_pedido_mencionado_en_el_hilo(self):
        resultado = resolver_referencia_pedido(
            "¿Cuál era el producto de ese pedido?",
            ["¿Cuál es el estado del pedido PED-1003?"],
        )
        self.assertIn("Pedido referido en esta conversación: PED-1003.", resultado)

    def test_02_no_toma_un_pedido_de_otro_hilo(self):
        consulta = "¿Cuál era el producto de ese pedido?"
        self.assertEqual(resolver_referencia_pedido(consulta, []), consulta)

    def test_03_prioriza_identificador_explicito_actual(self):
        consulta = "¿Cuál es el producto del pedido PED-1002?"
        self.assertEqual(
            resolver_referencia_pedido(consulta, ["Pedido PED-1003"]), consulta
        )

    def test_04_usa_la_mencion_mas_reciente(self):
        resultado = resolver_referencia_pedido(
            "¿Cuál es el estado de ese pedido?",
            ["Pedido PED-1001", "Gracias", "Pedido ped-1003"],
        )
        self.assertTrue(resultado.endswith("PED-1003."))

    def test_05_no_elige_entre_varios_pedidos(self):
        consulta = "¿Cuál era el producto de ese pedido?"
        self.assertEqual(
            resolver_referencia_pedido(
                consulta, ["Pedido PED-1001", "Compará PED-1002 y PED-1003"]
            ),
            consulta,
        )

    def test_06_conserva_consultas_generales_y_solicitudes_de_accion(self):
        for consulta in (
            "¿Qué pasa si llega dañado?",
            "¿Qué hago si el producto de ese pedido llega dañado?",
            "Quiero registrar un reclamo del producto de ese pedido.",
        ):
            with self.subTest(consulta=consulta):
                self.assertEqual(
                    resolver_referencia_pedido(consulta, ["Pedido PED-1003"]),
                    consulta,
                )


class MemoriaAgenteTests(unittest.TestCase):
    def test_07_seguimiento_y_fallback_consultan_el_pedido_recordado(self):
        # Los dobles prueban el enrutamiento sin ejecutar Ollama ni herramientas.
        from langchain_core.messages import AIMessage, HumanMessage
        from tecnosupply.aplicacion import agente

        previos = [
            HumanMessage(content="¿Cuál es el estado del pedido PED-1003?"),
            AIMessage(content="El producto es Mouse Logitech MX Master."),
        ]
        grafo = Mock()
        grafo.get_state.return_value = SimpleNamespace(values={"messages": previos})
        grafo.invoke.side_effect = lambda datos, config: {
            "messages": [
                *previos,
                *datos["messages"],
                AIMessage(content="El producto es Mouse Logitech MX Master."),
            ]
        }
        pedido = {
            "numero_pedido": "PED-1003",
            "estado": "en tránsito",
            "producto": "Mouse Logitech MX Master",
            "fecha_actualizacion": "2026-11-03 09:40",
        }
        consulta = "¿Cuál era el producto de ese pedido?"

        with (
            patch.object(agente, "AGENTE", grafo),
            patch.object(agente, "consultar_estado_pedido") as sensor,
            patch.object(agente, "buscar_conocimiento") as retriever,
        ):
            sensor.invoke.return_value = json.dumps(pedido)
            resultado = agente.consultar_agente_detallado(consulta, "hilo-memoria")

        sensor.invoke.assert_called_once_with({"numero_pedido": "PED-1003"})
        retriever.invoke.assert_not_called()
        self.assertEqual(resultado["herramientas"], ["consultar_estado_pedido"])
        self.assertIn("Mouse Logitech MX Master", resultado["respuesta"])
        mensaje = grafo.invoke.call_args.args[0]["messages"][0]
        self.assertIn("PED-1003", mensaje.content)
        self.assertEqual(mensaje.additional_kwargs["consulta_original"], consulta)
        self.assertEqual(
            grafo.get_state.call_args.args[0]["configurable"]["thread_id"],
            "hilo-memoria",
        )

    def test_08_historial_muestra_la_pregunta_original(self):
        from langchain_core.messages import HumanMessage
        from tecnosupply.aplicacion import agente

        consulta = "¿Cuál era el producto de ese pedido?"
        grafo = Mock()
        grafo.get_state.return_value = SimpleNamespace(values={"messages": [
            HumanMessage(
                content=f"{consulta}\nPedido referido en esta conversación: PED-1003.",
                additional_kwargs={"consulta_original": consulta},
            )
        ]})
        with patch.object(agente, "AGENTE", grafo):
            historial = agente.obtener_historial("hilo-memoria")
        self.assertEqual(historial, [{"rol": "usuario", "contenido": consulta}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
