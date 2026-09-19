from pathlib import Path
import json, re, math
import torch
from torch import nn

PAD = 0
UNK = 1

def normalize_text(s: str) -> str:
    s = str(s).strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s

def build_vocab(texts):
    chars = sorted(set("".join(normalize_text(t) for t in texts)))
    return {ch: i+2 for i, ch in enumerate(chars)}

def encode(text, vocab, max_len=96):
    text = normalize_text(text)[:max_len]
    ids = [vocab.get(ch, UNK) for ch in text]
    ids += [PAD] * (max_len - len(ids))
    return torch.tensor(ids, dtype=torch.long)

class CharFieldNet(nn.Module):
    """
    Character-level neural classifier for DIAN document fields.
    It is intentionally small and CPU-friendly.
    """
    def __init__(self, vocab_size, n_classes, emb=48, hidden=96, max_len=96):
        super().__init__()
        self.max_len = max_len
        self.embedding = nn.Embedding(vocab_size, emb, padding_idx=PAD)
        self.conv = nn.Conv1d(emb, 96, kernel_size=5, padding=2)
        self.gru = nn.GRU(96, hidden, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(0.20)
        self.fc = nn.Linear(hidden * 2, n_classes)

    def forward(self, x):
        e = self.embedding(x).transpose(1,2)
        c = torch.relu(self.conv(e)).transpose(1,2)
        out, _ = self.gru(c)
        mask = (x != PAD).unsqueeze(-1)
        out = out * mask
        denom = mask.sum(dim=1).clamp(min=1)
        pooled = out.sum(dim=1) / denom
        return self.fc(self.dropout(pooled))
