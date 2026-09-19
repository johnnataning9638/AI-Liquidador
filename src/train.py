from pathlib import Path
import json, random
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from model import build_vocab, encode, CharFieldNet

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "seed_dataset_v2.json"
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(exist_ok=True)

random.seed(42)
torch.manual_seed(42)

rows = json.loads(DATA.read_text(encoding="utf-8"))
labels = sorted({r["label"] for r in rows})
label_to_id = {x:i for i,x in enumerate(labels)}
texts = [r["text"] for r in rows]
vocab = build_vocab(texts)

by_label = {lab: [] for lab in labels}
for r in rows:
    by_label[r["label"]].append(r)

train_rows, val_rows = [], []
for lab, items in by_label.items():
    items = items[:]
    random.shuffle(items)
    cut = max(1, int(len(items) * 0.80))
    train_rows.extend(items[:cut])
    val_rows.extend(items[cut:] or items[:1])

def tensors(items):
    X = torch.stack([encode(r["text"], vocab) for r in items])
    y = torch.tensor([label_to_id[r["label"]] for r in items], dtype=torch.long)
    return X, y

Xtr, ytr = tensors(train_rows)
Xva, yva = tensors(val_rows)

model = CharFieldNet(len(vocab)+2, len(labels))
opt = torch.optim.AdamW(model.parameters(), lr=1.5e-3, weight_decay=1e-4)
loss_fn = nn.CrossEntropyLoss()
loader = DataLoader(TensorDataset(Xtr, ytr), batch_size=16, shuffle=True)

best = -1.0
best_state = None
for epoch in range(100):
    model.train()
    for xb, yb in loader:
        opt.zero_grad()
        loss = loss_fn(model(xb), yb)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        pred = model(Xva).argmax(1)
        acc = (pred == yva).float().mean().item()

    if acc > best:
        best = acc
        best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

model.load_state_dict(best_state)
torch.save({
    "state_dict": model.state_dict(),
    "vocab": vocab,
    "labels": labels,
    "max_len": model.max_len,
    "dataset_version": "v2",
}, MODEL_DIR / "field_classifier.pt")

# Per-class report
model.eval()
with torch.no_grad():
    pred = model(Xva).argmax(1)
report = {}
for lab in labels:
    idx = label_to_id[lab]
    mask = yva == idx
    report[lab] = {
        "n_validation": int(mask.sum().item()),
        "accuracy": float((pred[mask] == yva[mask]).float().mean().item()) if mask.any() else None
    }

(MODEL_DIR / "validation_report.json").write_text(
    json.dumps({"overall_accuracy": best, "by_class": report}, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"Modelo v2 guardado. Mejor validación: {best:.3f}")
for lab in labels:
    print(f"{lab}: {report[lab]['accuracy']}")
print("Nota: sigue siendo un dataset de desarrollo; no representa precisión sobre datos reales.")
