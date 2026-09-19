import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from parser import classify

cases = [
    ("900123456", "NIT"),
    ("800197268", "NIT"),
    ("901234567", "NIT"),
    ("890900123", "NIT"),
    ("900123456-7", "NIT"),
    ("4,9111E+12", "RECIBO"),
    ("3,0047E+12", "RECIBO"),
    ("Documento Fuente 4911100000000", "RECIBO"),
    ("TDJ 123456789", "TDJ"),
    ("Título de depósito judicial 456789012", "TDJ"),
    ("31/03/2026", "FECHA"),
    ("01 01 26", "FECHA"),
    ("4.137.000", "VALOR"),
    ("$95", "VALOR"),
]

for text, expected in cases:
    result = classify(text)
    print(f"{text} => {result['label']} | {result['confidence']} | {result['source']}")
    assert result["label"] == expected, (text, expected, result)

print("BENCHMARK OK")
