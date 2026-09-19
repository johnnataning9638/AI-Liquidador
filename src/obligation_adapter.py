from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from parser import classify, parse_date, parse_money, normalize_scientific


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", "" if v is None else str(v).replace("\u00a0", " ")).strip()


def digits(v: Any) -> str:
    return re.sub(r"\D", "", "" if v is None else str(v))


def year(v: Any) -> int:
    m = re.search(r"\b(20\d{2})\b", str(v or ""))
    return int(m.group(1)) if m else 0


def dates_in(text: str):
    out = []
    patterns = [
        r"\b\d{1,2}[/.\-]\d{1,2}[/.\-](?:20\d{2}|\d{2})\b",
        r"\b20\d{2}[/.\-]\d{1,2}[/.\-]\d{1,2}\b",
        r"\b\d{6}(?:\d{2})?\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            d = parse_date(m.group(0))
            if d:
                out.append((m.start(), m.group(0), d))
    return sorted({(i, raw, d) for i, raw, d in out}, key=lambda x: x[0])


def extract_nit(text: str) -> Dict[str, Any]:
    explicit = re.search(
        r"(?:N\.?\s*I\.?\s*T\.?|n[uú]mero\s+de\s+identificaci[oó]n|identificaci[oó]n\s+tributaria)\s*[:#\-]?\s*(\d{6,12})(?:\s*[-/]\s*\d)?",
        text, flags=re.I,
    )
    if explicit:
        return {"value": explicit.group(1), "confidence": 1.0, "source": "explicit"}
    candidates = []
    for m in re.finditer(r"\b\d{6,12}\b", text):
        s = m.group(0)
        if re.fullmatch(r"20\d{2}", s):
            continue
        score = 0.30
        ctx = text[max(0, m.start()-50):m.end()+50]
        if re.search(r"NIT|IDENTIFICACI[ÓO]N|TRIBUTARIA|DOCUMENTO", ctx, re.I): score += 0.55
        if s.startswith(("8", "9")) and len(s) == 9: score += 0.10
        if re.search(r"[.,]\d{3}", s): score -= 0.20
        candidates.append((score, s))
    if not candidates:
        return {"value": "", "confidence": 0.0, "source": "none"}
    candidates.sort(reverse=True)
    return {"value": candidates[0][1], "confidence": min(candidates[0][0], 0.99), "source": "inferred"}


def extract_reason(text: str) -> Dict[str, Any]:
    m = re.search(r"(?:raz[oó]n\s+social|nombre\s+(?:o\s+)?raz[oó]n|contribuyente)\s*[:#\-]?\s*([^\n\r]+)", text, re.I)
    if m:
        v = clean(m.group(1)).strip(" -:#")
        if v:
            return {"value": v.upper(), "confidence": 1.0, "source": "explicit"}
    suffix = re.compile(r"\b(?:SAS|S\.?A\.?S?\.?|LTDA\.?|LIMITADA|E\.?U\.?|COOPERATIVA|FUNDACI[ÓO]N|ASOCIACI[ÓO]N)\b", re.I)
    banned = re.compile(r"pegar|reconocer|informaci[oó]n|fecha|vencimiento|impuesto|cuota|periodo|vigencia|nit|identificaci[oó]n|tributaria", re.I)
    candidates = []
    for line in text.replace("\r", "").split("\n"):
        v = clean(line)
        if len(v) < 3 or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", v) or banned.search(v):
            continue
        # Remove obvious dates/numbers from the candidate line.
        vv = re.sub(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-](?:20\d{2}|\d{2})\b", " ", v)
        vv = re.sub(r"\b20\d{2}\b", " ", vv)
        vv = re.sub(r"(?:\$\s*)?(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d{4,})", " ", vv)
        vv = re.sub(r"(?<!\d)[-/]\s*\d{1,2}(?!\d)", " ", vv)
        vv = clean(vv).strip(" -:#")
        if len(vv) < 3 or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", vv):
            continue
        score = 0.35 + min(len(vv), 60)/200
        if suffix.search(vv): score += 0.45
        if len(vv.split()) >= 2: score += 0.10
        # Ask the field classifier for an additional semantic signal.
        try:
            cls = classify(vv)
            if cls.get("label") == "RAZON_SOCIAL": score += 0.10 * float(cls.get("confidence", 0))
        except Exception:
            pass
        candidates.append((min(score, 0.99), vv.upper()))
    if not candidates:
        return {"value": "", "confidence": 0.0, "source": "none"}
    candidates.sort(reverse=True)
    return {"value": candidates[0][1], "confidence": candidates[0][0], "source": "inferred"}


def extract_year(text: str, date_matches) -> Dict[str, Any]:
    protected = []
    for i, raw, _ in date_matches:
        protected.append((i, i + len(raw)))
    vals = []
    for m in re.finditer(r"\b20\d{2}\b", text):
        if any(a <= m.start() < b for a, b in protected):
            continue
        vals.append(int(m.group(0)))
    return {"value": vals[0] if vals else 0, "confidence": 0.95 if vals else 0.0, "source": "explicit" if vals else "none"}


def money_matches(text: str):
    out=[]
    pat=r"(?:\$\s*)?(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d{4,})"
    protected=[(i,i+len(raw)) for i,raw,_ in dates_in(text)]
    for m in re.finditer(pat, text):
        if any(a <= m.start() < b for a,b in protected):
            continue
        raw=m.group(0).replace("$", "").strip()
        if re.fullmatch(r"20\d{2}", raw):
            continue
        if re.fullmatch(r"\d{6}|\d{8}", raw) and parse_date(raw):
            continue
        n=parse_money(raw)
        if n is not None and n > 0:
            out.append((m.start(), raw, float(n)))
    return out


def cuota_number(ctx: str) -> Optional[int]:
    m=re.search(r"(?:cuota|periodo|vto|vencimiento)\s*(?:n(?:umero)?|no)?\s*(?:de)?\s*([1-6])\b", ctx, re.I)
    return int(m.group(1)) if m else None


def extract_cuotas(text: str, max_items: int=6) -> List[Dict[str, Any]]:
    ds=dates_in(text)
    ms=money_matches(text)
    if not ds:
        return []
    pairs=[]
    used=set()
    if len(ds)==len(ms):
        for i,(d,m) in enumerate(zip(ds,ms)):
            pairs.append((d,m,0.95))
    else:
        for d in ds:
            best=None
            for j,m in enumerate(ms):
                if j in used: continue
                dist=abs(m[0]-d[0])
                score=max(0.05,0.90-min(dist/2000,0.70))
                if best is None or score>best[0]: best=(score,j,m)
            if best:
                used.add(best[1]);pairs.append((d,best[2],best[0]))
    result=[]
    used_num=set()
    for d,m,conf in pairs:
        ctx=text[max(0,d[0]-60):d[0]+len(d[1])+60]
        n=cuota_number(ctx)
        if n and n not in used_num:
            used_num.add(n)
            result.append({"numero":n,"periodo":str(n),"fecha":d[2],"impuesto":m[2],"confidence":round(conf,4)})
    next_n=1
    for d,m,conf in pairs:
        if any(x["fecha"]==d[2] for x in result): continue
        while next_n in used_num and next_n<=6: next_n+=1
        if next_n>6: break
        used_num.add(next_n)
        result.append({"numero":next_n,"periodo":str(next_n),"fecha":d[2],"impuesto":m[2],"confidence":round(conf,4)})
    return sorted(result,key=lambda x:x["numero"])[:max_items]


def interpret_obligation(text: str) -> Dict[str, Any]:
    text=str(text or "")
    if not text.strip(): raise ValueError("No hay información para interpretar.")
    ds=dates_in(text)
    nit=extract_nit(text)
    reason=extract_reason(text)
    anio=extract_year(text,ds)
    cuotas=extract_cuotas(text)
    confs=[x["confidence"] for x in (nit,reason,anio) if x.get("confidence",0)>0]
    confs += [c.get("confidence",0) for c in cuotas]
    confidence=sum(confs)/len(confs) if confs else 0.0
    return {
        "orientation":"mixed",
        "confidence":round(confidence,4),
        "fields":{
            "nit":nit["value"],
            "razonSocial":reason["value"],
            "anio":anio["value"],
            "cuotas":cuotas,
        },
        "evidence":{
            "nit":nit,
            "razonSocial":reason,
            "anio":anio,
            "cuotas":cuotas,
        },
    }
