from structured import interpret
from payment_adapter import interpret_payments

TEXT = """4911098513361\t1\tRecibo Oficial de Pago Impuestos Nacionales AG 2006 y siguientes\t30/03/2026\tINICIAL\t3.047.000
4911098761609\t1\tRecibo Oficial de Pago Impuestos Nacionales AG 2006 y siguientes\t31/03/2026\tINICIAL\t10.924.000
3004724916099\t1\tImpuesto sobre las Ventas -IVA AG 2019 y siguientes\t3/04/2026\tVALIDA/ACTIVA
4911099025075\t1\tRecibo Oficial de Pago Impuestos Nacionales AG 2006 y siguientes\t4/04/2026\tINICIAL\t2.294.000"""

r = interpret_payments(TEXT)
assert len(r["records"]) == 4, r
assert r["records"][0]["recibo_no"] == "4911098513361", r
assert r["records"][0]["fecha_pago"] == "2026-03-30", r
assert r["records"][0]["valor_pago"] == 3047000, r
assert r["records"][1]["recibo_no"] == "4911098761609", r
assert r["records"][1]["valor_pago"] == 10924000, r
assert r["records"][2]["recibo_no"] == "3004724916099", r
assert r["records"][2]["valor_pago"] is None, r
assert r["records"][3]["recibo_no"] == "4911099025075", r
assert r["records"][3]["valor_pago"] == 2294000, r
print("MUISCA PAYMENT REGRESSION v0.6.5 OK")
