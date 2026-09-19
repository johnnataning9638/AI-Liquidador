from __future__ import annotations
import re
import json
from typing import List, Dict, Any, Tuple
from parser import classify, normalize_scientific, parse_date, parse_money, SCI_RE

FIELD_ALIASES = {
    "RECIBO": ["documento fuente", "recibo no", "recibo", "numero recibo", "número recibo", "no documento"],
    "TDJ": ["tdj", "titulo de deposito judicial", "título de depósito judicial"],
    "FECHA": ["fecha presentacion", "fecha presentación", "fecha pago", "fecha", "presentacion", "presentación"],
    "VALOR": ["valor pagado", "valor pago", "valor", "importe", "pago"],
    "ESTADO": ["estado"],
    "REPETICION": ["repeticion", "repetición"],
    "RAZON_SOCIAL": ["razon social", "razón social", "nombre"],
    "TEXTO": ["nombre formato", "formato", "clase documento"],
}

def clean_cell(v: Any) -> str:
    s = "" if v is None else str(v)
    s = s.replace("\u00a0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def split_pasted(text: str) -> List[List[str]]:
    """Parse clipboard-like text into a rectangular-ish matrix."""
    lines = [x for x in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    matrix = []
    for line in lines:
        if not line.strip():
            continue
        # Prefer explicit table delimiters. For unlabeled payment-like rows,
        # however, clipboard sources frequently convert tabs into spaces.
        # In that case split only on whitespace when the line contains at
        # least two strong structured tokens (date, money, scientific
        # document number or DIAN status). This preserves free-form names
        # and descriptions elsewhere.
        if "\t" in line:
            cells = line.split("\t")
        elif "|" in line:
            cells = line.split("|")
        elif ";" in line:
            cells = line.split(";")
        else:
            if re.search(r"\bTDJ\b|T[ÍI]TULO\s+DE\s+DEP[ÓO]SITO\s+JUDICIAL", line, flags=re.I):
                cells = [line]
                matrix.append([clean_cell(c) for c in cells])
                continue
            tokens = re.findall(r"[^\s]+", line)
            strong = 0
            for tok in tokens:
                if parse_date(tok) or parse_money(tok) is not None:
                    strong += 1
                    continue
                if SCI_RE.match(tok):
                    strong += 1
                    continue
                if re.fullmatch(r"INICIAL|VALIDA/?ACTIVA|VÁLIDA/?ACTIVA|CANCELADO|PAGADO|PENDIENTE", tok.upper()):
                    strong += 1
                    continue
                if re.search(r"\bTDJ\b|T[ÍI]TULO\s+DE\s+DEP[ÓO]SITO\s+JUDICIAL", tok.upper()):
                    strong += 1
            cells = tokens if strong >= 2 else [line]
        matrix.append([clean_cell(c) for c in cells])
    width = max((len(r) for r in matrix), default=0)
    return [r + [""] * (width - len(r)) for r in matrix]

def field_from_header(text: str):
    t = clean_cell(text).lower()
    if not t:
        return None
    for field, aliases in FIELD_ALIASES.items():
        if any(a in t for a in aliases):
            return field
    return None

def classify_cell(text: str) -> Dict[str, Any]:
    s = clean_cell(text)
    if not s:
        return {"label": None, "confidence": 0.0, "source": "empty"}
    return classify(s)

def looks_like_header_row(row: List[str]) -> bool:
    return sum(field_from_header(c) is not None for c in row) >= 2

def transpose(m):
    if not m:
        return []
    return [list(x) for x in zip(*m)]

def score_orientation(m: List[List[str]]) -> float:
    if not m:
        return -1
    score = 0.0
    for row in m:
        for cell in row:
            f = field_from_header(cell)
            if f:
                score += 4
            else:
                result = classify_cell(cell)
                if result["label"] in {"RECIBO","TDJ","FECHA","VALOR","NIT","ESTADO","REPETICION"}:
                    score += 0.15 * result["confidence"]
    return score

def choose_orientation(m):
    mt = transpose(m)
    a = score_orientation(m)
    b = score_orientation(mt)
    return (m, "rows", a) if a >= b else (mt, "columns", b)

def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    if record.get("RECIBO"):
        raw = record["RECIBO"]
        if re.search(r"[Ee][+\-]?\d+", raw):
            out["numero"] = normalize_scientific(raw)
        else:
            digits = re.sub(r"\D", "", raw)
            out["numero"] = digits or raw
        out["tipo_documento"] = "RECIBO"
    elif record.get("TDJ"):
        raw = str(record["TDJ"])
        m = re.search(
            r"(?:\bTDJ\b|T[ÍI]TULO\s+DE\s+DEP[ÓO]SITO\s+JUDICIAL)\s*[:#N°º-]?\s*(\d{5,})",
            raw, flags=re.I
        )
        number = m.group(1) if m else raw
        out["numero"] = re.sub(r"\D", "", number) or number
        out["tipo_documento"] = "TDJ"

    if record.get("FECHA"):
        d = parse_date(record["FECHA"])
        if d:
            out["fecha"] = d
    if record.get("VALOR") is not None:
        v = parse_money(record["VALOR"])
        if v is not None:
            out["valor"] = v
    for k in ["ESTADO","REPETICION","RAZON_SOCIAL","TEXTO"]:
        if record.get(k) not in (None, ""):
            out[k.lower()] = record[k]
    return out

def records_from_labeled_matrix(m: List[List[str]]) -> List[Dict[str, Any]]:
    """Handles a matrix where one row/column contains field labels."""
    if not m:
        return []

    # Header orientation: first row labels.
    if looks_like_header_row(m[0]):
        headers = [field_from_header(c) for c in m[0]]
        records = []
        for row in m[1:]:
            rec = {}
            for i, val in enumerate(row):
                if i < len(headers) and headers[i] and val:
                    rec[headers[i]] = val
            if rec:
                records.append(normalize_record(rec))
        return [r for r in records if r]

    # Transposed style: first column labels, subsequent columns are records.
    label_count = sum(field_from_header(row[0]) is not None for row in m if row)
    if label_count >= 2:
        records = []
        width = max(len(r) for r in m)
        for col in range(1, width):
            rec = {}
            for row in m:
                if not row:
                    continue
                f = field_from_header(row[0])
                if f and col < len(row) and row[col]:
                    rec[f] = row[col]
            if rec:
                records.append(normalize_record(rec))
        return [r for r in records if r]

    return []


def digits_for_tdj(value: Any) -> str:
    return re.sub(r"\D", "", "" if value is None else str(value))

def _assign_unlabeled_cell(rec: Dict[str, Any], cell: str):
    c = clean_cell(cell)
    if not c:
        return
    up = c.upper()

    # Long plain MUISCA document numbers are deterministic and must be
    # classified as documents before generic money detection. Otherwise a
    # receipt such as 4911098513361 is incorrectly treated as the payment
    # value, while a descriptive cell containing the word RECIBO becomes the
    # document.
    if re.fullmatch(r"\d{12,}", c):
        rec["RECIBO"] = c
        return
    if SCI_RE.match(c):
        n = normalize_scientific(c)
        if n.isdigit() and len(n) >= 13:
            rec["RECIBO"] = n
            return

    # Strong semantic markers first.
    if re.search(r"\bTDJ\b|T[ÍI]TULO DE DEP[ÓO]SITO JUDICIAL", up):
        if "TDJ" not in rec:
            m = re.search(
                r"(?:\bTDJ\b|T[ÍI]TULO\s+DE\s+DEP[ÓO]SITO\s+JUDICIAL)\s*[:#N°º-]?\s*(\d{5,})",
                c, flags=re.I
            )
            rec["TDJ"] = (m.group(1).strip() if m else c)
        dm = re.search(r"(?<!\d)(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})(?!\d)", c)
        if dm and "FECHA" not in rec:
            rec["FECHA"] = dm.group(1)
        # Capture grouped money after the TDJ number/date when present.
        money_tokens = re.findall(r"(?<![\d.,])\$?\d{1,3}(?:[.,]\d{3})+(?![\d.,])|(?<!\d)\d{2,}(?!\d)", c)
        if money_tokens and "VALOR" not in rec:
            for tok in reversed(money_tokens):
                if tok not in digits_for_tdj(rec.get("TDJ", "")):
                    rec["VALOR"] = tok
                    break
        return
    if re.search(r"\bNIT\b|\bIDENTIFICACI[ÓO]N\b", up):
        if "NIT" not in rec:
            rec["NIT"] = c
        return

    # A bare "1" in MUISCA payment rows is the repetition/occurrence field,
    # not the payment value. Resolve it before the generic classifier, which
    # correctly treats standalone digits as money in other contexts.
    if c == "1" and ("RECIBO" in rec or "TDJ" in rec):
        rec["REPETICION"] = c
        return

    result = classify_cell(c)
    label = result["label"]

    if label in {"RECIBO", "TDJ"}:
        key = label
        if key not in rec:
            rec[key] = c
        return

    if label == "FECHA" and "FECHA" not in rec:
        rec["FECHA"] = c
        return

    if label == "VALOR" and "VALOR" not in rec:
        rec["VALOR"] = c
        return

    if label == "ESTADO" and "ESTADO" not in rec:
        rec["ESTADO"] = c
        return

    # Repetition is recognized only when explicitly labeled.
    if re.fullmatch(r"(REPETICI[ÓO]N\s*:?)\s*[1-9]\d*", up):
        rec["REPETICION"] = re.sub(r"[^0-9]", "", c)
        return

    # Exact bare "1" is treated as repetition only if a record already has a
    # document/date/value, avoiding collision with monetary amounts.
    if re.fullmatch(r"\d+", c) and c == "1" and (
        "RECIBO" in rec or "TDJ" in rec
    ) and ("FECHA" in rec or "VALOR" in rec):
        rec["REPETICION"] = c
        return

def records_from_unlabeled(m: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Reconstruct unlabeled records.
    - Each non-empty row is first treated as a candidate record.
    - Cell order is irrelevant.
    - If a row contains only part of a record, consecutive rows are merged
      until a document boundary is encountered.
    """
    candidates = []

    for row in m:
        rec = {}
        for cell in row:
            _assign_unlabeled_cell(rec, cell)
        if rec:
            candidates.append(rec)

    # If rows already look like complete records, keep them separate.
    def has_identity(r):
        return "RECIBO" in r or "TDJ" in r

    complete = [
        r for r in candidates
        if has_identity(r) and ("FECHA" in r or "VALOR" in r)
    ]
    if len(complete) == len(candidates) and complete:
        return [normalize_record(r) for r in complete]

    # Merge partial rows around document boundaries.
    merged = []
    current = {}
    for r in candidates:
        if has_identity(r) and has_identity(current):
            merged.append(normalize_record(current))
            current = {}
        current.update(r)
    if current:
        merged.append(normalize_record(current))

    # Remove empty/duplicate records.
    out = []
    seen = set()
    for r in merged:
        if not r:
            continue
        key = json.dumps(r, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def interpret(text: str) -> Dict[str, Any]:
    matrix = split_pasted(text)
    if not matrix:
        return {"orientation": "unknown", "records": [], "confidence": 0.0}

    # Remove empty edge columns created by copied Markdown/table delimiters.
    while matrix and all(not x for x in matrix[0]):
        matrix.pop(0)
    while matrix and all(not row[-1] for row in matrix):
        for row in matrix:
            row.pop()

    # Payment-like MUISCA rows must be evaluated before generic labeled-table
    # detection. Descriptions such as "Recibo Oficial de Pago..." contain the
    # word RECIBO and can otherwise be mistaken for a header, causing the AI
    # adapter to return records like {recibo_no: "Recibo"} with no date/value.
    # A deterministic row signature (long document + date + money/status) has
    # priority over the generic header classifier.
    def looks_like_payment_matrix(m):
        hits = 0
        for row in m:
            cells = [clean_cell(c) for c in row if clean_cell(c)]
            has_doc = any(
                (re.fullmatch(r"4\d{12,}", c) is not None)
                or (SCI_RE.match(c) and normalize_scientific(c).isdigit() and len(normalize_scientific(c)) >= 13)
                or re.search(r"\bTDJ\b|T[ÍI]TULO\s+DE\s+DEP[ÓO]SITO\s+JUDICIAL", c, re.I)
                for c in cells
            )
            has_date = any(parse_date(c) for c in cells)
            has_money = any(parse_money(c) is not None for c in cells)
            has_status = any(re.fullmatch(r"INICIAL|VALIDA/?ACTIVA|VÁLIDA/?ACTIVA|CANCELADO|PAGADO|PENDIENTE", c, re.I) for c in cells)
            if has_doc and has_date and (has_money or has_status):
                hits += 1
        return hits > 0

    if looks_like_payment_matrix(matrix):
        payment_records = records_from_unlabeled(matrix)
        complete = [r for r in payment_records if r.get("numero") and r.get("fecha") and r.get("valor") is not None]
        if complete:
            return {"orientation": "rows", "records": payment_records, "confidence": 0.995}

    # First attempt: labeled table as pasted.
    direct = records_from_labeled_matrix(matrix)
    if direct:
        return {"orientation": "labeled", "records": direct, "confidence": 0.98}

    # Then transposed/labeled orientation.
    mt = transpose(matrix)
    transposed = records_from_labeled_matrix(mt)
    if transposed:
        return {"orientation": "transposed", "records": transposed, "confidence": 0.97}

    # Finally try both row-wise and transposed row-wise grouping.
    # Prefer the orientation that creates more complete records, not merely
    # the orientation with more individually classifiable cells.
    row_records = records_from_unlabeled(matrix)
    col_records = records_from_unlabeled(transpose(matrix))

    def completeness(records):
        if not records:
            return (0, 0, 0)
        complete = 0
        fields = 0
        for r in records:
            keys = set(r.keys())
            if ("numero" in keys and "fecha" in keys and "valor" in keys):
                complete += 1
            fields += len(keys)
        return (complete, len(records), fields)

    rs = completeness(row_records)
    cs = completeness(col_records)

    if rs >= cs:
        records, orientation = row_records, "rows"
    else:
        records, orientation = col_records, "columns"

    return {"orientation": orientation, "records": records,
            "confidence": 0.90 if records else 0.0}
