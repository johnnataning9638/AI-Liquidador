from obligation_adapter import interpret_obligation
from payment_adapter import interpret_payments

OBL = """NIT: 900123456-7
RAZÓN SOCIAL: EMPRESA EJEMPLO SAS
AÑO GRAVABLE: 2025
CUOTA 1 30/04/2025 $1.200.000
CUOTA 2 30/06/2025 $800.000"""
PAY = """4,9111E+12 05/03/2026 INICIAL 4.137.000
18/03/2026 3.579.000 4,9111E+12 INICIAL
TDJ 123456789 10/04/2026 157"""

o=interpret_obligation(OBL); p=interpret_payments(PAY)
assert o["fields"]["nit"] == "900123456"
assert o["fields"]["razonSocial"] == "EMPRESA EJEMPLO SAS"
assert len(o["fields"]["cuotas"]) == 2
assert p["records"][0]["recibo_no"] == "4911100000000"
assert p["records"][2]["tdj_no"] == "123456789"
assert p["records"][2]["valor_pago"] == 157
print("CASE INTEGRATION OK")
