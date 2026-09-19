from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
LABELS_FILE = BASE / "data" / "labels.json"


def allowed_labels() -> set[str]:
    return set(json.loads(LABELS_FILE.read_text(encoding="utf-8")))


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


def save_feedback(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL no está configurada")
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
        f"{url}/rest/v1/ai_feedback",
        data=json.dumps(clean, ensure_ascii=False).encode("utf-8"),
        headers=_supabase_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else []


def fetch_feedback() -> list[dict[str, Any]]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL no está configurada")
    query = urllib.parse.urlencode({
        "select": "id,text,label,source,created_at",
        "confirmed": "eq.true",
        "processed_at": "is.null",
        "order": "id.asc",
        "limit": "10000",
    })
    req = urllib.request.Request(
        f"{url}/rest/v1/ai_feedback?{query}",
        headers=_supabase_headers(),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def finalize_training(ids: list[int], training_run_id: str, retain_per_label: int = 10) -> None:
    """Mark accepted examples as processed and prune processed non-retained rows.

    The newest ``retain_per_label`` rows per label are retained as a small
    safety memory; older processed rows are deleted to keep Supabase small.
    """
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not url or not ids:
        return
    headers = _supabase_headers()
    headers["Prefer"] = "return=minimal"
    now_payload = json.dumps({
        "processed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "training_run_id": training_run_id,
    }).encode("utf-8")
    for row_id in ids:
        req = urllib.request.Request(
            f"{url}/rest/v1/ai_feedback?id=eq.{int(row_id)}",
            data=now_payload, headers=headers, method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=15):
            pass

    # Keep only the newest retained examples per label. This is intentionally
    # conservative: processed examples remain available until a later cleanup.
    labels = sorted(allowed_labels())
    for label in labels:
        query = urllib.parse.urlencode({
            "select": "id",
            "label": f"eq.{label}",
            "processed_at": "not.is.null",
            "order": "id.desc",
            "limit": str(retain_per_label),
        })
        req = urllib.request.Request(f"{url}/rest/v1/ai_feedback?{query}", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            keep_rows = json.loads(resp.read().decode("utf-8"))
        keep_ids = {int(r["id"]) for r in keep_rows}
        if not keep_ids:
            continue
        # Delete older processed rows for this label, excluding the retained set.
        # Supabase/PostgREST supports NOT IN through the `not.in.(...)` filter.
        keep_csv = ",".join(str(x) for x in sorted(keep_ids))
        delete_query = urllib.parse.urlencode({
            "label": f"eq.{label}",
            "processed_at": "not.is.null",
            "id": f"not.in.({keep_csv})",
        })
        req = urllib.request.Request(
            f"{url}/rest/v1/ai_feedback?{delete_query}",
            headers=headers, method="DELETE"
        )
        with urllib.request.urlopen(req, timeout=15):
            pass
