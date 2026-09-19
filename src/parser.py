from pathlib import Path
import re
from predict import predict

DATE_RE = re.compile(r"^\s*(\d{1,2})[\/\-. ](\d{1,2})[\/\-. ](\d{2,4})\s*$")
SCI_RE = re.compile(r"^\s*[\d\.,]+[Ee][+\-]?\d+\s*$")
NIT_PLAIN_RE = re.compile(r"^\s*[89]\d{8}\s*$")
NIT_WITH_DV_RE = re.compile(r"^\s*[89]\d{8}\s*[-–]\s*\d\s*$")

def normalize_scientific(value: str) -> str:
    s = str(value).strip().replace(",", ".")
    if not SCI_RE.match(s):
        return re.sub(r"[^\d]", "", str(value))
    try:
        return str(int(float(s)))
    except Exception:
        return str(value).strip()

def parse_date(value):
    m = DATE_RE.match(str(value))
    if not m:
        return None
    d, mo, y = map(int, m.groups())
    if y < 100:
        y += 2000 if y <= 69 else 1900
    try:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    except ValueError:
        return None

def parse_money(value):
    s = str(value).strip().replace("$","").replace(" ","")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return int(re.sub(r"[.,]", "", s))
    if s.isdigit():
        return int(s)
    return None

def classify(text):
    s = str(text).strip()
    up = s.upper()

    # 1. Explicit semantic markers always win.
    if re.search(r"\bTDJ\b|T[ÍI]TULO DE DEP[ÓO]SITO JUDICIAL", up):
        return {"label": "TDJ", "confidence": 1.0, "source": "deterministic"}

    if re.search(r"\bNIT\b|\bIDENTIFICACI[ÓO]N\b", up):
        return {"label": "NIT", "confidence": 1.0, "source": "deterministic"}

    if re.search(r"DOCUMENTO\s+FUENTE|RECIBO\s*(NO|N[ÚU]MERO)?", up):
        return {"label": "RECIBO", "confidence": 1.0, "source": "deterministic"}

    # 2. Dates are structurally unambiguous.
    if parse_date(s):
        return {"label": "FECHA", "confidence": 1.0, "source": "deterministic"}

    # 3. Scientific notation with a large document-like magnitude is a
    #    common Excel/MUISCA representation of a long source-document number.
    if SCI_RE.match(s):
        try:
            n = float(s.replace(",", "."))
            if n >= 1e11:
                return {"label": "RECIBO", "confidence": 0.995, "source": "deterministic"}
        except Exception:
            pass

    # 4. Plain NIT shape gets priority over generic numeric value.
    #    Colombian NITs commonly have 9 base digits; an optional DV may follow.
    if NIT_PLAIN_RE.match(s) or NIT_WITH_DV_RE.match(s):
        return {"label": "NIT", "confidence": 0.99, "source": "deterministic"}

    # 5. Common DIAN/MUISCA status and repetition markers.
    if re.fullmatch(r"INICIAL|VALIDA/?ACTIVA|VÁLIDA/?ACTIVA|CANCELADO|PAGADO|PENDIENTE", up):
        return {"label": "ESTADO", "confidence": 1.0, "source": "deterministic"}

    if re.fullmatch(r"(REPETICI[ÓO]N\\s*:?)?\\s*[1-9]\\d*", up):
        # A bare integer is ambiguous with money; repetition is resolved by
        # context in the structured interpreter. Do not force it here.
        pass

    # 6. Explicit monetary formatting / grouped thousands.
    if parse_money(s) is not None:
        return {"label": "VALOR", "confidence": 0.99, "source": "deterministic"}

    # 6. Ambiguous text is delegated to the neural model.
    p = predict(s)
    p["source"] = "neural"
    return p
