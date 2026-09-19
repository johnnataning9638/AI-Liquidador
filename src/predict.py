from pathlib import Path
import sys, json
import torch
from model import CharFieldNet, encode, normalize_text

BASE = Path(__file__).resolve().parents[1]
CKPT = BASE / "models" / "field_classifier.pt"

def load():
    ckpt = torch.load(CKPT, map_location="cpu")
    model = CharFieldNet(len(ckpt["vocab"])+2, len(ckpt["labels"]), max_len=ckpt["max_len"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt["vocab"], ckpt["labels"]

def predict(text):
    model, vocab, labels = load()
    x = encode(text, vocab).unsqueeze(0)
    with torch.no_grad():
        p = torch.softmax(model(x), dim=1)[0]
    conf, idx = torch.max(p, 0)
    return {"text": text, "label": labels[idx.item()], "confidence": float(conf)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python src/predict.py "texto a clasificar"')
        raise SystemExit(1)
    print(json.dumps(predict(" ".join(sys.argv[1:])), ensure_ascii=False, indent=2))
