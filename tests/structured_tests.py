import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from structured import interpret

HORIZONTAL = """Documento Fuente\tFecha Presentacion\tValor Pagado\tEstado
4,9111E+12\t5/03/2026\t4.137.000\tINICIAL
4,9111E+12\t18/03/2026\t3.579.000\tINICIAL"""

VERTICAL = """Documento Fuente\t4,9111E+12\t4,9111E+12
Fecha Presentacion\t5/03/2026\t18/03/2026
Valor Pagado\t4.137.000\t3.579.000
Estado\tINICIAL\tINICIAL"""

UNLABELED = """INICIAL\t4,9111E+12\t5/03/2026\t4.137.000
INICIAL\t4,9111E+12\t18/03/2026\t3.579.000"""

def test_horizontal():
    r = interpret(HORIZONTAL)
    assert len(r["records"]) == 2
    assert r["records"][0]["numero"] == "4911100000000"
    assert r["records"][0]["fecha"] == "2026-03-05"
    assert r["records"][0]["valor"] == 4137000

def test_vertical():
    r = interpret(VERTICAL)
    assert len(r["records"]) == 2
    assert r["records"][1]["fecha"] == "2026-03-18"
    assert r["records"][1]["valor"] == 3579000

def test_unlabeled():
    r = interpret(UNLABELED)
    assert len(r["records"]) == 2
    assert r["records"][0]["numero"] == "4911100000000"
    assert r["records"][0]["fecha"] == "2026-03-05"
    assert r["records"][0]["valor"] == 4137000
    assert r["records"][1]["fecha"] == "2026-03-18"

if __name__ == "__main__":
    test_horizontal()
    test_vertical()
    test_unlabeled()
    print("STRUCTURED TESTS OK")


ARBITRARY_ORDER = """4.137.000\tINICIAL\t5/03/2026\t4,9111E+12
3.579.000\t18/03/2026\t4,9111E+12\tINICIAL"""

DISORDERED_SINGLE = """4.137.000
INICIAL
5/03/2026
4,9111E+12"""

def test_arbitrary_order():
    r = interpret(ARBITRARY_ORDER)
    assert len(r["records"]) == 2
    assert r["records"][0]["numero"] == "4911100000000"
    assert r["records"][0]["fecha"] == "2026-03-05"
    assert r["records"][0]["valor"] == 4137000
    assert r["records"][1]["fecha"] == "2026-03-18"

def test_disordered_single():
    r = interpret(DISORDERED_SINGLE)
    assert len(r["records"]) == 1
    assert r["records"][0]["numero"] == "4911100000000"
    assert r["records"][0]["fecha"] == "2026-03-05"
    assert r["records"][0]["valor"] == 4137000

if __name__ == "__main__":
    test_horizontal()
    test_vertical()
    test_unlabeled()
    test_arbitrary_order()
    test_disordered_single()
    print("STRUCTURED TESTS V0.5 OK")
