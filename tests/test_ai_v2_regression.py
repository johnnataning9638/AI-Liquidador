import unittest
from unittest.mock import patch

from parser import classify
from learning import normalize_memory_text


class AIV2RegressionTests(unittest.TestCase):
    def test_deterministic_fields_never_depend_on_neural_model(self):
        cases = {
            "TDJ 123456": "TDJ",
            "NIT 901234567": "NIT",
            "RECIBO 4901234567890": "RECIBO",
            "01/09/2026": "FECHA",
            "$ 3.047.000": "VALOR",
            "3.047.000": "VALOR",
        }
        for text, expected in cases.items():
            result = classify(text)
            self.assertEqual(result["label"], expected, (text, result))

    def test_memory_normalization(self):
        self.assertEqual(
            normalize_memory_text("  Valor   $ 3.047.000 "),
            "valor $ 3.047.000",
        )

    def test_memory_is_optional(self):
        with patch("parser.find_memory", return_value=None):
            result = classify("texto ambiguo de prueba")
        self.assertTrue(result["label"])

    def test_parser_does_not_import_tax_motor(self):
        import parser
        self.assertNotIn("motor-liquidacion", str(parser.__file__))


if __name__ == "__main__":
    unittest.main()
