from __future__ import annotations

import unittest

from PAGINAS_DO_SISTEMA.RELATORIO_ESTOQUE_IA import EstoqueIA
from PAGINAS_DO_SISTEMA.ESTOQUE_IA_LAB import (
    executar_rodadas,
    gerar_rodadas_massivas,
    gerar_rodadas_rigorosas,
    RODADAS_TREINO,
)


class EstoqueIATests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_carregar = EstoqueIA._carregar_memoria_persistente
        self._orig_persistir = EstoqueIA._persistir_memoria_persistente
        EstoqueIA._carregar_memoria_persistente = lambda self: None
        EstoqueIA._persistir_memoria_persistente = lambda self, snapshot: None

        self.ia = EstoqueIA()
        self.ia._base_dataset = lambda: [
            {
                "grupo_principal": "Tecidos",
                "familia": "textil",
                "codigo": "TEC-001",
                "descricao": "Malha Canelada",
                "subgrupo": "malha",
                "categoria": "canelado",
                "cor": "preto",
                "fornecedor": "Fornecedor A",
                "localizacao": "Prateleira 1",
                "composicao": "algodao",
                "unidade": "m",
                "saldo_num": 35,
                "estoque_minimo": 10,
                "estoque_ideal": 50,
                "consumo_medio": 2,
            },
            {
                "grupo_principal": "Tecidos",
                "familia": "textil",
                "codigo": "TEC-002",
                "descricao": "Malha Canelada",
                "subgrupo": "malha",
                "categoria": "canelado",
                "cor": "azul",
                "fornecedor": "Fornecedor B",
                "localizacao": "Prateleira 2",
                "composicao": "algodao",
                "unidade": "m",
                "saldo_num": 5,
                "estoque_minimo": 10,
                "estoque_ideal": 50,
                "consumo_medio": 2,
            },
            {
                "grupo_principal": "Aviamentos",
                "familia": "acabamento",
                "codigo": "ZIP-010",
                "descricao": "Ziper Nylon",
                "subgrupo": "ziper",
                "categoria": "fechamento",
                "cor": "preto",
                "fornecedor": "Casa do Ziper",
                "localizacao": "Gaveta 3",
                "unidade": "un",
                "saldo_num": 200,
                "estoque_minimo": 50,
            },
        ]

    def tearDown(self) -> None:
        EstoqueIA._carregar_memoria_persistente = self._orig_carregar
        EstoqueIA._persistir_memoria_persistente = self._orig_persistir

    def test_understands_natural_item_and_context_followups(self) -> None:
        resposta = self.ia.responder("tem malha canelada?")
        self.assertIn("Malha Canelada", resposta)

        resposta = self.ia.responder("e preta?")
        self.assertIn("cor preto", resposta)
        self.assertIn("Malha Canelada", resposta)

        resposta = self.ia.responder("quem fornece?")
        self.assertIn("Fornecedor A", resposta)

    def test_fuzzy_search_handles_typo(self) -> None:
        resposta = self.ia.responder("tem ziper prto")

        self.assertIn("Ziper Nylon", resposta)

    def test_group_action_is_not_misread_as_item_name(self) -> None:
        entidades = self.ia._extract_entities("quais tecidos estao criticos")

        self.assertIsNone(entidades["item_nome"])
        self.assertEqual(entidades["grupo"], "Tecidos")

        resposta = self.ia.responder("quais tecidos estao criticos")
        self.assertIn("1 item", resposta)

    def test_training_lab_rounds_pass(self) -> None:
        resultado = executar_rodadas(verbose=False)

        self.assertEqual(resultado["falhas"], [])
        self.assertEqual(resultado["ok"], resultado["total"])

    def test_rigorous_training_rounds_pass(self) -> None:
        resultado = executar_rodadas(rodadas=[*RODADAS_TREINO, *gerar_rodadas_rigorosas()], verbose=False)

        self.assertEqual(resultado["falhas"], [])
        self.assertEqual(resultado["ok"], resultado["total"])
        self.assertGreaterEqual(resultado["total"], 250)

    def test_conversation_real_examples_are_handled(self) -> None:
        rodadas = gerar_rodadas_massivas(minimo_perguntas=1000)[-2:]
        resultado = executar_rodadas(rodadas=rodadas, verbose=False)

        self.assertEqual(resultado["falhas"], [])
        self.assertEqual(resultado["ok"], resultado["total"])

    def test_massive_training_rounds_over_1000_questions_pass(self) -> None:
        rodadas = [
            *RODADAS_TREINO,
            *gerar_rodadas_rigorosas(),
            *gerar_rodadas_massivas(minimo_perguntas=1200),
        ]
        resultado = executar_rodadas(rodadas=rodadas, verbose=False)

        self.assertEqual(resultado["falhas"], [])
        self.assertEqual(resultado["ok"], resultado["total"])
        self.assertGreaterEqual(resultado["total"], 1000)


if __name__ == "__main__":
    unittest.main()
