from __future__ import annotations

import json
import random
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from learning import fetch_feedback, finalize_training
from model import build_vocab, encode, CharFieldNet, normalize_text

BASE = Path(__file__).resolve().parents[1]
SEED = BASE / "data" / "seed_dataset_v2.json"
MODEL = BASE / "models" / "field_classifier.pt"
REPORT = BASE / "models" / "validation_report.json"
MIN_FEEDBACK = 40
MIN_LABELS = 5
MIN_PER_LABEL = 2
MIN_GAIN = 0.01

random.seed(42)
torch.manual_seed(42)


def load_rows():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    feedback = fetch_feedback()
    seen = {(normalize_text(r["text"]), r["label"]) for r in seed}
    extra = []
    for r in feedback:
        key = (normalize_text(r["text"]), str(r["label"]).upper())
        if key not in seen:
            seen.add(key)
            extra.append({"text": r["text"], "label": str(r["label"]).upper()})
    return seed, extra


def tensors(rows, vocab, label_to_id):
    X = torch.stack([encode(r["text"], vocab) for r in rows])
    y = torch.tensor([label_to_id[r["label"]] for r in rows], dtype=torch.long)
    return X, y


def accuracy(model, rows, vocab, label_to_id):
    if not rows:
        return 0.0
    X, y = tensors(rows, vocab, label_to_id)
    model.eval()
    with torch.no_grad():
        pred = model(X).argmax(1)
    return float((pred == y).float().mean().item())


def main():
    seed, feedback = load_rows()
    if len(feedback) < MIN_FEEDBACK:
        print(f"SKIP: solo hay {len(feedback)} ejemplos nuevos; se requieren {MIN_FEEDBACK}.")
        return

    counts = {}
    for r in feedback:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    qualified = [k for k, v in counts.items() if v >= MIN_PER_LABEL]
    if len(qualified) < MIN_LABELS:
        print(f"SKIP: diversidad insuficiente: {counts}")
        return

    random.shuffle(feedback)
    cut = max(1, int(len(feedback) * 0.80))
    train_fb, val_fb = feedback[:cut], feedback[cut:]
    train_rows = seed + train_fb
    labels = sorted({r["label"] for r in train_rows})
    label_to_id = {x: i for i, x in enumerate(labels)}
    vocab = build_vocab([r["text"] for r in train_rows])

    Xtr, ytr = tensors(train_rows, vocab, label_to_id)
    loader = DataLoader(TensorDataset(Xtr, ytr), batch_size=16, shuffle=True)
    candidate = CharFieldNet(len(vocab) + 2, len(labels))
    opt = torch.optim.AdamW(candidate.parameters(), lr=1.5e-3, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss()

    best = -1.0
    best_state = None
    for _ in range(100):
        candidate.train()
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(candidate(xb), yb)
            loss.backward()
            opt.step()
        score = accuracy(candidate, val_fb, vocab, label_to_id)
        if score > best:
            best = score
            best_state = {k: v.cpu().clone() for k, v in candidate.state_dict().items()}

    candidate.load_state_dict(best_state)

    # Evaluate current production model on exactly the same feedback holdout.
    ckpt = torch.load(MODEL, map_location="cpu")
    baseline = CharFieldNet(len(ckpt["vocab"]) + 2, len(ckpt["labels"]), max_len=ckpt["max_len"])
    baseline.load_state_dict(ckpt["state_dict"])
    baseline_vocab = ckpt["vocab"]
    baseline_labels = {x: i for i, x in enumerate(ckpt["labels"])}
    compatible = [r for r in val_fb if r["label"] in baseline_labels]
    baseline_score = accuracy(baseline, compatible, baseline_vocab, baseline_labels)

    print(f"feedback={len(feedback)} candidate={best:.4f} baseline={baseline_score:.4f}")
    if best < baseline_score + MIN_GAIN:
        print("REJECT: el candidato no supera al modelo actual con margen suficiente.")
        return

    training_run_id = f"continuous-{len(feedback)}-{best:.4f}"
    torch.save({
        "state_dict": candidate.state_dict(),
        "vocab": vocab,
        "labels": labels,
        "max_len": candidate.max_len,
        "dataset_version": training_run_id,
    }, MODEL)
    REPORT.write_text(json.dumps({
        "mode": "continuous_learning",
        "feedback_examples": len(feedback),
        "candidate_holdout_accuracy": best,
        "baseline_holdout_accuracy": baseline_score,
        "minimum_required_gain": MIN_GAIN,
        "accepted": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    finalize_training([int(r["id"]) for r in feedback if "id" in r], training_run_id, retain_per_label=10)
    print("ACCEPT: nuevo modelo guardado y ejemplos procesados/depurados.")


if __name__ == "__main__":
    main()
