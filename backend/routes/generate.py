from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import time
import threading
import json
import httpx
import base64
import asyncio

from services.ai_service import generate_slide_content
from services.pptx_service import build_presentation
from services.pdf_service import build_presenter_pdf

router = APIRouter()

TTL_SECONDS     = 60 * 60  # 1 hour
PAYMONGO_SECRET = os.environ.get("PAYMONGO_SECRET_KEY", "")
FRONTEND_URL    = os.environ.get("FRONTEND_URL", "https://pptprov2.vercel.app")

# ── Disk-persisted download token store ───────────────────────────────────────
_STORE_FILE = os.path.join(
    os.environ.get("STORE_DIR", os.path.dirname(__file__)), ".token_store.json"
)
_store: Dict[str, Dict] = {}
_store_lock = threading.Lock()

# ── In-memory payment job store ───────────────────────────────────────────────
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()


def _load_store():
    global _store
    try:
        if os.path.exists(_STORE_FILE):
            with open(_STORE_FILE, "r") as f:
                data = json.load(f)
            now = time.time()
            _store = {k: v for k, v in data.items() if v.get("expires", 0) > now}
            print(f"🗂️  Token store loaded: {len(_store)} active token(s)")
    except Exception as e:
        print(f"⚠️  Could not load token store: {e}")
        _store = {}


def _save_store():
    try:
        with open(_STORE_FILE, "w") as f:
            json.dump(_store, f)
    except Exception as e:
        print(f"⚠️  Could not save token store: {e}")


def _cleanup_expired():
    now = time.time()
    with _store_lock:
        expired = [k for k, v in _store.items() if now > v.get("expires", 0)]
        if not expired:
            return
        for k in expired:
            entry = _store.pop(k)
            for key in ("pptx_path", "pdf_path"):
                p = entry.get(key)
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except Exception:
                        pass
        _save_store()


def _save_token(pptx_path: str, pdf_path: Optional[str], filename_base: str) -> str:
    _cleanup_expired()
    token = uuid.uuid4().hex
    with _store_lock:
        _store[token] = {
            "pptx_path":     pptx_path,
            "pdf_path":      pdf_path,
            "filename_base": filename_base,
            "expires":       time.time() + TTL_SECONDS,
        }
        _save_store()
    return token


def _get_entry(token: str) -> Dict:
    _cleanup_expired()
    with _store_lock:
        entry = _store.get(token)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Download link expired or not found. Please generate again."
        )
    if not (entry.get("pptx_path") and os.path.exists(entry["pptx_path"])):
        raise HTTPException(
            status_code=404,
            detail="Generated files were lost (server restart). Please generate again."
        )
    return entry


_load_store()


# ── Request models ─────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    subject: str
    level: str
    title: str
    language: str
    instructions: Optional[str] = ""


class CreatePaymentRequest(BaseModel):
    amount: int
    method: str
    title: str
    want_pdf: bool
    subject: str
    level: str
    language: str
    instructions: Optional[str] = ""


def _safe_title(title: str) -> str:
    return title.replace(" ", "_").replace("/", "-").replace("\\", "-")[:60]


def _cleanup_paths(*paths):
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass


# ── PayMongo checkout session ──────────────────────────────────────────────────
async def _create_paymongo_checkout(amount: int, method: str, description: str, ref: str) -> str:
    auth = base64.b64encode(f"{PAYMONGO_SECRET}:".encode()).decode()
    method_map = {"gcash": ["gcash"], "card": ["card"]}
    payment_method_types = method_map.get(method, ["gcash"])

    payload = {
        "data": {
            "attributes": {
                "billing": {
                    "name":  "pptPro Customer",
                    "email": "customer@pptpro.app",
                },
                "line_items": [
                    {
                        "currency": "PHP",
                        "amount":   amount,
                        "name":     description[:100],
                        "quantity": 1,
                    }
                ],
                "payment_method_types": payment_method_types,
                "success_url": f"{FRONTEND_URL}?payment=success&ref={ref}",
                "cancel_url":  f"{FRONTEND_URL}?payment=cancelled&ref={ref}",
                "metadata":    {"ref": ref},
            }
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.paymongo.com/v1/checkout_sessions",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type":  "application/json",
            },
            json=payload,
        )
        if not res.is_success:
            raise HTTPException(status_code=502, detail=f"PayMongo error: {res.json()}")
        return res.json()["data"]["attributes"]["checkout_url"]


# ── Background generation ──────────────────────────────────────────────────────
async def _run_generation(ref: str, job: Dict):
    pptx_path = None
    pdf_path  = None
    try:
        with _jobs_lock:
            _jobs[ref]["status"] = "processing"

        slides = await generate_slide_content(
            subject=job["subject"],
            level=job["level"],
            title=job["title"],
            language=job["language"],
            instructions=job.get("instructions", ""),
        )

        pptx_path = build_presentation(
            slides=slides, title=job["title"], subject=job["subject"],
            level=job["level"], language=job["language"],
        )

        if job.get("want_pdf"):
            pdf_path = build_presenter_pdf(
                slides=slides, title=job["title"], subject=job["subject"],
                level=job["level"], language=job["language"],
            )

        token = _save_token(pptx_path, pdf_path, _safe_title(job["title"]))

        with _jobs_lock:
            _jobs[ref].update({
                "status":  "ready",
                "token":   token,
                "has_pdf": pdf_path is not None,
            })
        print(f"✅ Generation done for ref {ref}")

    except Exception as e:
        print(f"❌ Generation error for ref {ref}: {e}")
        _cleanup_paths(pptx_path, pdf_path)
        with _jobs_lock:
            _jobs[ref]["status"] = "failed"


# ── POST /api/create-payment ───────────────────────────────────────────────────
@router.post("/create-payment")
async def create_payment(req: CreatePaymentRequest):
    if not PAYMONGO_SECRET:
        raise HTTPException(status_code=503, detail="Payment not configured on server.")

    ref = uuid.uuid4().hex

    with _jobs_lock:
        _jobs[ref] = {
            "status":       "pending",
            "title":        req.title,
            "subject":      req.subject,
            "level":        req.level,
            "language":     req.language,
            "instructions": req.instructions or "",
            "want_pdf":     req.want_pdf,
            "created_at":   time.time(),
        }

    checkout_url = await _create_paymongo_checkout(
        amount=req.amount,
        method=req.method,
        description=f"pptPro: {req.title[:80]}",
        ref=ref,
    )

    return {"checkout_url": checkout_url, "ref": ref}


# ── POST /api/webhook ──────────────────────────────────────────────────────────
@router.post("/webhook")
async def paymongo_webhook(request: Request):
    """
    Register this URL in PayMongo Dashboard → Developers → Webhooks:
    URL:    https://pptprov2-backend.onrender.com/api/webhook
    Events: checkout_session.payment.paid
    """
    try:
        body       = await request.json()
        event_type = body.get("data", {}).get("attributes", {}).get("type", "")

        if event_type not in ("checkout_session.payment.paid", "payment.paid"):
            return {"received": True}

        # Extract ref from metadata
        attrs    = body.get("data", {}).get("attributes", {})
        metadata = attrs.get("data", {}).get("attributes", {}).get("metadata") or \
                   attrs.get("metadata") or {}
        ref = metadata.get("ref", "")

        if not ref:
            print("⚠️  Webhook: no ref in metadata")
            return {"received": True}

        with _jobs_lock:
            job = _jobs.get(ref)

        if not job or job["status"] != "pending":
            return {"received": True}

        asyncio.create_task(_run_generation(ref, dict(job)))
        print(f"🚀 Generation started for ref {ref}")

    except Exception as e:
        print(f"⚠️  Webhook error: {e}")

    return {"received": True}  # Always 200 to PayMongo


# ── GET /api/payment-status/{ref} ─────────────────────────────────────────────
@router.get("/payment-status/{ref}")
def payment_status(ref: str):
    with _jobs_lock:
        job = _jobs.get(ref)

    if not job:
        raise HTTPException(status_code=404, detail="Payment reference not found.")

    status = job.get("status", "pending")

    if status == "ready":
        return {
            "status":  "ready",
            "token":   job.get("token"),
            "has_pdf": job.get("has_pdf", False),
            "title":   job.get("title"),
            "subject": job.get("subject"),
        }

    return {"status": status}


# ── POST /generate (legacy / local dev) ───────────────────────────────────────
@router.post("/generate")
async def generate_presentation(req: GenerateRequest):
    pptx_path = None
    try:
        slides = await generate_slide_content(
            subject=req.subject, level=req.level, title=req.title,
            language=req.language, instructions=req.instructions,
        )
        pptx_path = build_presentation(
            slides=slides, title=req.title, subject=req.subject,
            level=req.level, language=req.language,
        )
        token = _save_token(pptx_path, None, _safe_title(req.title))
        return {"token": token, "has_pdf": False, "expires_in": TTL_SECONDS}

    except HTTPException:
        raise
    except ValueError as e:
        _cleanup_paths(pptx_path)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"❌ Error: {e}")
        _cleanup_paths(pptx_path)
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /generate/both (legacy / local dev) ──────────────────────────────────
@router.post("/generate/both")
async def generate_both(req: GenerateRequest):
    pptx_path = None
    pdf_path  = None
    try:
        slides = await generate_slide_content(
            subject=req.subject, level=req.level, title=req.title,
            language=req.language, instructions=req.instructions,
        )
        pptx_path = build_presentation(
            slides=slides, title=req.title, subject=req.subject,
            level=req.level, language=req.language,
        )
        pdf_path = build_presenter_pdf(
            slides=slides, title=req.title, subject=req.subject,
            level=req.level, language=req.language,
        )
        token = _save_token(pptx_path, pdf_path, _safe_title(req.title))
        return {"token": token, "has_pdf": True, "expires_in": TTL_SECONDS}

    except HTTPException:
        raise
    except ValueError as e:
        _cleanup_paths(pptx_path, pdf_path)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"❌ Both error: {e}")
        _cleanup_paths(pptx_path, pdf_path)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /download/{token}/pptx ─────────────────────────────────────────────────
@router.get("/download/{token}/pptx")
def download_pptx(token: str):
    entry = _get_entry(token)
    path  = entry["pptx_path"]
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PPTX file no longer available.")
    filename = f"{entry['filename_base']}_pptPro.pptx"
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


# ── GET /download/{token}/pdf ──────────────────────────────────────────────────
@router.get("/download/{token}/pdf")
def download_pdf(token: str):
    entry = _get_entry(token)
    path  = entry.get("pdf_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF file not available.")
    filename = f"{entry['filename_base']}_pptPro_Notes.pdf"
    return FileResponse(path=path, media_type="application/pdf", filename=filename)


# ── GET /status ────────────────────────────────────────────────────────────────
@router.get("/status")
def api_status():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    return {
        "api_configured":     bool(key),
        "payment_configured": bool(PAYMONGO_SECRET),
        "status": "ready" if key else "missing_api_key",
    }