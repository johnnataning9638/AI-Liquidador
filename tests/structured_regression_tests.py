import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from structured import interpret

def test_horizontal_spaces():
    text = "4.137.000    INICIAL    5/03/2026    4,9111E+12"
    r = interpret(text)
    assert len(r["records"]) == 1
    assert r["records"][0]["numero"] == "4911100000000"
    assert r["records"][0]["fecha"] == "2026-03-05"
    assert r["records"][0]["valor"] == 4137000

def test_vertical():
    text = "4,9111E+12\nINICIAL\n5/03/2026\n4.137.000"
    r = interpret(text)
    assert len(r["records"]) == 1
    assert r["records"][0]["numero"] == "4911100000000"
    assert r["records"][0]["fecha"] == "2026-03-05"
    assert r["records"][0]["valor"] == 4137000

def test_tdj_text():
    text = "TDJ 123456789\n10/04/2026\n157"
    r = interpret(text)
    assert len(r["records"]) == 1
    assert r["records"][0]["tipo_documento"] == "TDJ"
    assert r["records"][0]["numero"] == "123456789"
    assert r["records"][0]["valor"] == 157

if __name__ == "__main__":
    test_horizontal_spaces()
    test_vertical()
    test_tdj_text()
    print("STRUCTURED REGRESSION TESTS V0.6.3 OK")
