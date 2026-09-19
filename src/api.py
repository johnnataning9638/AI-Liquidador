from pathlib import Path
import sys
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import time

from parser import classify
from payment_adapter import interpret_payments
from obligation_adapter import interpret_obligation

ENGINE_VERSION = "0.6.6"

app = FastAPI(title="DIAN AI Engine", version=ENGINE_VERSION)

# Lightweight local-service guard: avoid accidental request floods without
# introducing external infrastructure. This is not an authentication system.
_REQUEST_WINDOW = 60.0
_REQUEST_MAX = 120
_request_times = []

def _rate_guard():
    now = time.monotonic()
    while _request_times and now - _request_times[0] > _REQUEST_WINDOW:
        _request_times.pop(0)
    if len(_request_times) >= _REQUEST_MAX:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes al AI Engine. Espere un momento.")
    _request_times.append(now)

# The web Liquidador may run from GitHub Pages or localhost. The AI engine is
# normally a local companion service, so CORS is enabled for browser clients.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class Item(BaseModel):
    text: str = Field(min_length=1, max_length=1_000_000)

class PaymentInterpretation(BaseModel):
    text: str = Field(min_length=1, max_length=1_000_000)

class CaseInterpretation(BaseModel):
    obligation_text: str = Field(default="", max_length=1_000_000)
    payments_text: str = Field(default="", max_length=1_000_000)


@app.middleware("http")
async def local_guard(request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        _rate_guard()
    return await call_next(request)

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "dian-ai-engine",
        "version": ENGINE_VERSION,
        "capabilities": ["classify", "interpret_payments", "interpret_obligation", "interpret_case"],
        "stability": {"contract": "1.0", "max_input_chars": 1_000_000, "rate_limit_per_minute": _REQUEST_MAX},
    }

@app.post("/classify")
def classify_item(item: Item):
    return classify(item.text)

@app.post("/interpret/payments")
def interpret_payment_data(item: PaymentInterpretation) -> Dict[str, Any]:
    try:
        result = interpret_payments(item.text)
        return {
            "ok": True,
            "service": "dian-ai-engine",
            "version": ENGINE_VERSION,
            **result,
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"No fue posible interpretar los pagos: {exc}")


@app.post("/interpret/obligation")
def interpret_obligation_data(item: Item) -> Dict[str, Any]:
    try:
        result = interpret_obligation(item.text)
        return {
            "ok": True,
            "service": "dian-ai-engine",
            "version": ENGINE_VERSION,
            **result,
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"No fue posible interpretar la obligación: {exc}")


@app.post("/interpret/case")
def interpret_case(item: CaseInterpretation) -> Dict[str, Any]:
    try:
        obligation = interpret_obligation(item.obligation_text) if item.obligation_text.strip() else {"fields": {}, "confidence": 0.0, "records": []}
        payments = interpret_payments(item.payments_text) if item.payments_text.strip() else {"records": [], "confidence": 0.0}
        return {
            "ok": True,
            "service": "dian-ai-engine",
            "version": ENGINE_VERSION,
            "obligation": obligation,
            "payments": payments,
            "confidence": round((float(obligation.get("confidence",0))+float(payments.get("confidence",0)))/2,4),
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"No fue posible interpretar el caso completo: {exc}")
