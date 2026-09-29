from pathlib import Path
import sys, json
import torch
from model import CharFieldNet, encode, normalize_text

# Keep the small classifier resident in the Render worker. The previous
# implementation rebuilt and reloaded the PyTorch checkpoint for every
# ambiguous cell, which multiplied latency for pasted tables.
_MODEL_CACHE = None

def _configure_cpu():
    try:
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass

BASE = Path(__file__).resolve().parents[1]
CKPT = BASE / "models" / "field_classifier.pt"

def load():
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    _configure_cpu()
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = CharFieldNet(len(ckpt["vocab"])+2, len(ckpt["labels"]), max_len=ckpt["max_len"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    _MODEL_CACHE = (model, ckpt["vocab"], ckpt["labels"])
    return _MODEL_CACHE

def predict(text):
    model, vocab, labels = load()
    x = encode(text, vocab).unsqueeze(0)
    with torch.inference_mode():
        p = torch.softmax(model(x), dim=1)[0]
    conf, idx = torch.max(p, 0)
    return {"text": text, "label": labels[idx.item()], "confidence": float(conf)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python src/predict.py "texto a clasificar"')
        raise SystemExit(1)
    print(json.dumps(predict(" ".join(sys.argv[1:])), ensure_ascii=False, indent=2))
