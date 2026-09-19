import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from structured import interpret

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python src/interpret.py "texto pegado"')
        raise SystemExit(1)
    text = " ".join(sys.argv[1:])
    print(json.dumps(interpret(text), ensure_ascii=False, indent=2))
