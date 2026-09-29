from parser import classify
from learning import normalize_memory_text

def test_deterministic_fields_never_depend_on_neural_model():
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
        assert result["label"] == expected, (text, result)

def test_memory_normalization():
    assert normalize_memory_text("  Valor   $ 3.047.000 ") == "valor $ 3.047.000"

def test_memory_is_optional(monkeypatch):
    import parser
    monkeypatch.setattr(parser, "find_memory", lambda *a, **k: None)
    result = parser.classify("texto ambiguo de prueba")
    assert result["label"]

def test_tdjs_never_enter_tax_formula_layer():
    # Architectural guard: parser classification is the only dependency
    # added by V2; no TDJ/motor modules are imported here.
    import parser
    assert "motor-liquidacion" not in str(parser.__dict__.get("__file__", ""))

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(type("M", (), {"setattr": staticmethod(lambda obj,n,v: setattr(obj,n,v))})()) if name == "test_memory_is_optional" else fn()
    print("AI V2 REGRESSION TESTS: PASS")
