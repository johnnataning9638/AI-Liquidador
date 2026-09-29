from __future__ import annotations

import json
import os
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
LABELS_FILE = BASE / "data" / "labels.json"

def allowed_labels() -> set[str]:
    return set(json.loads(LABELS_FILE.read_text(encoding="utf-8")))

def normalize_memory_text(value: str) -> str:
    s = unicodedata.normalize("NFD", str(value or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.strip().lower().split())

def _supabase_headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no está configurada")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def _supabase_url() -> str:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL no está configurada")
    return url

def _rpc(name: str, payload: dict[str, Any], timeout: int = 15) -> Any:
    req = urllib.request.Request(
        f"{_supabase_url()}/rest/v1/rpc/{name}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=_supabase_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else None

def find_memory(text: str, min_similarity: float = 0.92, limit: int = 3) -> dict[str, Any] | None:
    normalized = normalize_memory_text(text)
    if not normalized:
        return None
    try:
        rows = _rpc("ai_memory_match", {
            "p_text": normalized,
            "p_min_similarity": float(min_similarity),
            "p_limit": int(limit),
        }, timeout=3)
    except Exception:
        # La memoria es una mejora; nunca debe impedir la clasificación normal.
        return None
    if not isinstance(rows, list) or not rows:
        return None

    ranked = []
    for row in rows:
        try:
            sim = float(row.get("similarity", 0))
            correct = int(row.get("times_correct", 0))
            corrected = int(row.get("times_corrected", 0))
            if corrected > correct and corrected >= 2:
                continue
            ranked.append((sim, correct, row))
        except Exception:
            continue
    if not ranked:
        return None
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = ranked[0]
    if len(ranked) > 1:
        second = ranked[1]
        if best[2].get("label") != second[2].get("label") and (best[0] - second[0]) < 0.05:
            return None
    row = best[2]
    return {
        "label": str(row.get("label", "")).upper(),
        "confidence": min(1.0, max(0.0, float(best[0]))),
        "source": "memory",
        "memory_id": row.get("id"),
        "similarity": float(best[0]),
    }

def record_memory(text: str, label: str, source: str = "liquidador", confidence: float = 1.0, corrected: bool = False) -> None:
    normalized = normalize_memory_text(text)
    label = str(label or "").strip().upper()
    if not normalized or label not in allowed_labels():
        return
    try:
        _rpc("ai_memory_record", {
            "p_normalized_text": normalized,
            "p_label": label,
            "p_source": str(source or "liquidador")[:80],
            "p_confidence": float(confidence),
            "p_corrected": bool(corrected),
        }, timeout=5)
    except Exception:
        # Never make feedback fail just because the memory layer is unavailable.
        return

def save_feedback(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = []
    labels = allowed_labels()
    for e in examples:
        text = str(e.get("text", "")).strip()
        label = str(e.get("label", "")).strip().upper()
        if not text or len(text) > 5000 or label not in labels:
            continue
        clean.append({
            "text": text,
            "label": label,
            "source": str(e.get("source", "liquidador"))[:80],
            "confirmed": True,
        })
    if not clean:
        return []

    req = urllib.request.Request(
        f"{_supabase_url()}/rest/v1/ai_feedback",
        data=json.dumps(clean, ensure_ascii=False).encode("utf-8"),
        headers=_supabase_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    rows = json.loads(body) if body else []

    for e in clean:
        record_memory(e["text"], e["label"], e["source"], 1.0, corrected=False)
    return rows

def fetch_feedback(all_confirmed: bool = False) -> list[dict[str, Any]]:
    params = {
        "select": "id,text,label,source,created_at",
        "confirmed": "eq.true",
        "order": "id.asc",
        "limit": "10000",
    }
    if not all_confirmed:
        params["processed_at"] = "is.null"
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{_supabase_url()}/rest/v1/ai_feedback?{query}",
        headers=_supabase_headers(),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def finalize_training(ids: list[int], training_run_id: str, retain_per_label: int = 10) -> None:
    """Mark accepted examples as processed but keep them permanently for audit/memory."""
    if not ids:
        return
    headers = _supabase_headers()
    headers["Prefer"] = "return=minimal"
    now_payload = json.dumps({
        "processed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "training_run_id": training_run_id,
        "retained": True,
    }).encode("utf-8")
    for row_id in ids:
        req = urllib.request.Request(
            f"{_supabase_url()}/rest/v1/ai_feedback?id=eq.{int(row_id)}",
            data=now_payload, headers=headers, method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=15):
            pass
