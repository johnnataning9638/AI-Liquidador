from __future__ import annotations
import re
from typing import Any, Dict, List

TDJ_PATTERNS = (
    # Capture the TDJ number itself, not a following date/value on the same line.
    r"\bTDJ\b\s*[:#N°º-]?\s*(\d{5,})",
    r"T[ÍI]TULO\s+DE\s+DEP[ÓO]SITO\s+JUDICIAL\s*[:#N°º-]?\s*(\d{5,})",
)

def digits(value: Any) -> str:
    return re.sub(r"\D", "", "" if value is None else str(value))

def normalize_doc(value: Any) -> str:
    s = "" if value is None else str(value).strip()
    # Scientific notation is normalized by the existing structured layer.
    if re.search(r"[Ee][+\-]?\d+", s):
        try:
            from parser import normalize_scientific
            return normalize_scientific(s)
        except Exception:
            pass
    return digits(s) or s

def detect_tdj(text: Any) -> str | None:
    s = "" if text is None else str(text)
    for pattern in TDJ_PATTERNS:
        m = re.search(pattern, s, flags=re.I)
        if m:
            n = digits(m.group(1))
            if n:
                return n
    return None



def normalize_payment_value(value: Any):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    s = str(value).strip().replace("$", "").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        try:
            return int(re.sub(r"[.,]", "", s))
        except Exception:
            return None
    if re.fullmatch(r"\d+", s):
        try:
            return int(s)
        except Exception:
            return None
    return None

def payment_row(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an interpreted AI record into the Liquidador payment-table schema.
    This layer only structures data; it never imputes tax, interest or sanction.
    """
    tdj = detect_tdj(record.get("TDJ")) or detect_tdj(record.get("texto"))
    doc = record.get("numero", "")
    tipo = str(record.get("tipo_documento", "")).upper()

    if tdj or tipo == "TDJ":
        tipo = "TDJ"
        tdj_no = tdj or normalize_doc(doc)
        recibo = ""
    else:
        recibo = normalize_doc(doc) if tipo == "RECIBO" or doc else ""
        tdj_no = ""

    fecha = record.get("fecha", "") or ""
    valor = normalize_payment_value(record.get("valor", None))
    # Confidence is a structural signal, not a tax decision.  It reflects only
    # how completely the AI reconstructed this payment record.
    score = 0.0
    if tdj_no or recibo:
        score += 0.35
    if fecha:
        score += 0.30
    if valor is not None and valor > 0:
        score += 0.30
    if tipo in {"TDJ", "RECIBO"}:
        score += 0.05
    confidence = round(min(score, 0.99), 4)
    anomalies = []
    if not (tdj_no or recibo): anomalies.append("SIN_DOCUMENTO")
    if not fecha: anomalies.append("SIN_FECHA")
    if valor is None or valor <= 0: anomalies.append("SIN_VALOR_POSITIVO")
    return {
        "tdj_no": tdj_no,
        "recibo_no": recibo,
        "fecha_pago": fecha,
        "valor_pago": valor,
        "tipo": tipo or "RECIBO",
        "tasa": record.get("tasa", ""),
        "observacion": record.get("observacion", ""),
        "confidence": confidence,
        "anomalies": anomalies,
    }

def to_payment_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [payment_row(r) for r in records if r]

def interpret_payments(text: str) -> Dict[str, Any]:
    from structured import interpret
    result = interpret(text)
    rows = to_payment_rows(result.get("records", []))
    valid_conf = [float(r.get("confidence", 0)) for r in rows if r.get("confidence") is not None and not r.get("anomalies")]
    overall = min([float(result.get("confidence", 0.0))] + valid_conf) if valid_conf else float(result.get("confidence", 0.0))
    anomalies = [
        {"index": i + 1, "documento": r.get("tdj_no") or r.get("recibo_no") or "", "items": r.get("anomalies", [])}
        for i, r in enumerate(rows) if r.get("anomalies")
    ]
    return {
        "orientation": result.get("orientation"),
        "confidence": round(overall, 4),
        "records": rows,
        "anomalies": anomalies,
    }
