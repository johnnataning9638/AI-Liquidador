import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from obligation_adapter import interpret_obligation

SAMPLE = """NIT: 900123456-7
RAZÓN SOCIAL: EMPRESA DE PRUEBA S.A.S.
AÑO GRAVABLE: 2025
CUOTA 1 15/04/2026 $ 1.200.000
CUOTA 2 15/06/2026 $ 800.000
"""

r = interpret_obligation(SAMPLE)
assert r["fields"]["nit"] == "900123456"
assert r["fields"]["razonSocial"] == "EMPRESA DE PRUEBA S.A.S."
assert r["fields"]["anio"] == 2025
assert len(r["fields"]["cuotas"]) == 2
assert r["fields"]["cuotas"][0]["impuesto"] == 1200000
assert r["fields"]["cuotas"][1]["impuesto"] == 800000
print("OBLIGATION ADAPTER TESTS V0.6.3 OK")
