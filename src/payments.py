from __future__ import annotations
import sys, json
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from structured import interpret
from payment_adapter import to_payment_rows

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python src/payments.py <archivo.txt>")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8-sig")
    interpreted = interpret(text)
    result = {
        "orientation": interpreted.get("orientation"),
        "confidence": interpreted.get("confidence", 0.0),
        "records": to_payment_rows(interpreted.get("records", [])),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
