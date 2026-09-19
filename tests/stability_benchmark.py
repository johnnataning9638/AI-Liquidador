import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from payment_adapter import interpret_payments
from obligation_adapter import interpret_obligation

PAY = """4911098513361\t1\tRecibo Oficial de Pago Impuestos Nacionales AG 2006 y siguientes\t30/03/2026\tINICIAL\t3.047.000
4911098761609\t1\tRecibo Oficial de Pago Impuestos Nacionales AG 2006 y siguientes\t31/03/2026\tINICIAL\t10.924.000
3004724916099\t1\tImpuesto sobre las Ventas -IVA AG 2019 y siguientes\t3/04/2026\tVALIDA/ACTIVA
4911099025075\t1\tRecibo Oficial de Pago Impuestos Nacionales AG 2006 y siguientes\t4/04/2026\tINICIAL\t2.294.000"""

r = interpret_payments(PAY)
assert len(r["records"]) == 4
assert r["records"][0]["recibo_no"] == "4911098513361"
assert r["records"][0]["fecha_pago"] == "2026-03-30"
assert r["records"][0]["valor_pago"] == 3047000
assert all("confidence" in x for x in r["records"])
assert r["records"][0]["confidence"] >= 0.99
assert r["records"][2]["anomalies"]

OB = "NIT: 900123456\nRAZON SOCIAL: EMPRESA DEMO SAS\nAÑO GRAVABLE 2025\nCUOTA 1 15/04/2026 $1.200.000\nCUOTA 2 15/06/2026 $800.000"
o = interpret_obligation(OB)
assert o["fields"]["nit"] == "900123456"
assert len(o["fields"]["cuotas"]) == 2
assert 0 <= float(o.get("confidence", 0)) <= 1

print("STABILITY BENCHMARK v0.6.6 OK")
print(f"payments={len(r['records'])}; payment_confidence={r['confidence']}")
print(f"obligation_confidence={o.get('confidence')}; quotas={len(o['fields']['cuotas'])}")
