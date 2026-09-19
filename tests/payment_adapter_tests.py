import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from payment_adapter import payment_row, interpret_payments
from structured import interpret

def test_receipt():
    r = payment_row({
        "numero": "4911100000000",
        "tipo_documento": "RECIBO",
        "fecha": "2026-03-05",
        "valor": 4137000,
        "estado": "INICIAL",
    })
    assert r["tdj_no"] == ""
    assert r["recibo_no"] == "4911100000000"
    assert r["fecha_pago"] == "2026-03-05"
    assert r["valor_pago"] == 4137000
    assert r["tipo"] == "RECIBO"

def test_tdj():
    r = payment_row({
        "TDJ": "TDJ 123456789",
        "fecha": "2026-04-10",
        "valor": 157,
    })
    assert r["tdj_no"] == "123456789"
    assert r["recibo_no"] == ""
    assert r["tipo"] == "TDJ"
    assert r["valor_pago"] == 157

def test_tdj_title():
    r = payment_row({
        "texto": "Título de depósito judicial 456789012",
        "fecha": "2026-04-11",
        "valor": 1000,
    })
    assert r["tdj_no"] == "456789012"
    assert r["recibo_no"] == ""
    assert r["tipo"] == "TDJ"

def test_scientific_receipt():
    r = payment_row({
        "numero": "4,9111E+12",
        "tipo_documento": "RECIBO",
        "fecha": "2026-03-18",
        "valor": 3579000,
    })
    assert r["recibo_no"] == "4911100000000"


def test_tdj_full_pipeline():
    result = interpret_payments("TDJ 123456789\n10/04/2026\n157")
    assert len(result["records"]) == 1
    row = result["records"][0]
    assert row["tdj_no"] == "123456789"
    assert row["recibo_no"] == ""
    assert row["tipo"] == "TDJ"
    assert row["valor_pago"] == 157

def test_tdj_same_line_pipeline():
    result = interpret_payments("TDJ 123456789 10/04/2026 157")
    assert len(result["records"]) == 1
    row = result["records"][0]
    assert row["tdj_no"] == "123456789"
    assert row["fecha_pago"] == "2026-04-10"
    assert row["valor_pago"] == 157


def test_horizontal_payment_pipeline():
    result = interpret_payments("4.137.000    INICIAL    5/03/2026    4,9111E+12")
    row = result["records"][0]
    assert row["recibo_no"] == "4911100000000"
    assert row["fecha_pago"] == "2026-03-05"
    assert row["valor_pago"] == 4137000

def test_vertical_payment_pipeline():
    result = interpret_payments("4,9111E+12\nINICIAL\n5/03/2026\n4.137.000")
    row = result["records"][0]
    assert row["recibo_no"] == "4911100000000"
    assert row["fecha_pago"] == "2026-03-05"
    assert row["valor_pago"] == 4137000

def test_unlabeled_whitespace_rows():
    text = """4.137.000    INICIAL    5/03/2026    4,9111E+12
18/03/2026    3.579.000    4,9111E+12    INICIAL
4,9111E+12    21/03/2026    INICIAL    2.093.000"""
    result = interpret(text)
    assert len(result["records"]) == 3
    assert result["records"][0]["numero"] == "4911100000000"
    assert result["records"][0]["valor"] == 4137000
    assert result["records"][1]["fecha"] == "2026-03-18"

def test_eight_muisca_records():
    path = Path(__file__).resolve().parents[1] / "data" / "muisca_8_registros.txt"
    result = interpret(path.read_text(encoding="utf-8-sig"))
    assert len(result["records"]) == 8
    assert result["records"][6]["numero"] == "3004700000000"
    assert result["records"][6]["fecha"] == "2026-04-03"
    assert "valor" not in result["records"][6]

def test_eight_payment_rows():
    path = Path(__file__).resolve().parents[1] / "data" / "muisca_8_registros.txt"
    result = interpret_payments(path.read_text(encoding="utf-8-sig"))
    rows = result["records"]
    assert len(rows) == 8
    assert rows[0]["recibo_no"] == "4911100000000"
    assert rows[0]["valor_pago"] == 4137000
    assert rows[6]["recibo_no"] == "3004700000000"
    assert rows[6]["valor_pago"] is None

if __name__ == "__main__":
    test_receipt()
    test_tdj()
    test_tdj_title()
    test_scientific_receipt()
    test_tdj_full_pipeline()
    test_tdj_same_line_pipeline()
    test_horizontal_payment_pipeline()
    test_vertical_payment_pipeline()
    test_unlabeled_whitespace_rows()
    test_eight_muisca_records()
    test_eight_payment_rows()
    print("PAYMENT ADAPTER TESTS V0.6.3 OK")
