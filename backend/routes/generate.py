from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os
import uuid
import time
import threading
import json
import httpx
import base64
import asyncio
import hmac
import hashlib
from collections import defaultdict

from services.ai_service import generate_slide_content
from services.pptx_service import build_presentation
from services.pdf_service import build_presenter_pdf

router = APIRouter()

TTL_SECONDS     = 60 * 60  # 1 hour
PAYMONGO_SECRET = os.environ.get("PAYMONGO_SECRET_KEY", "")
PAYMONGO_WEBHOOK_SECRET = os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
FRONTEND_URL    = os.environ.get("FRONTEND_URL", "https://pptprov2.vercel.app")

# ── Legacy route guard ─────────────────────────────────────────────────────────
# Set ENABLE_LEGACY_ROUTES=true in .env for local dev only.
# NEVER set this on Render — legacy routes have no payment check.
_LEGACY_ENABLED = os.environ.get("ENABLE_LEGACY_ROUTES", "false").strip().lower() == "true"

# ── Disk-persisted download token store ───────────────────────────────────────
_STORE_FILE = os.path.join(
    os.environ.get("STORE_DIR", os.path.dirname(__file__)), ".token_store.json"
)
_store: Dict[str, Dict] = {}
_store_lock = threading.Lock()

# ── Disk-persisted payment job store ─────────────────────────────────────────
_JOBS_FILE = os.path.join(
    os.environ.get("STORE_DIR", os.path.dirname(__file__)), ".jobs_store.json"
)
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()

# ── In-memory rate limiter ────────────────────────────────────────────────────
# Tracks request timestamps per IP per endpoint category.
# Using a simple sliding-window approach — no Redis needed on free tier.
_rate_data: Dict[str, list] = defaultdict(list)
_rate_lock = threading.Lock()

RATE_LIMITS = {
    # (max_requests, window_seconds)
    "payment":  (5,  60 * 10),   # 5 payment attempts per 10 minutes per IP
    "webhook":  (20, 60),        # 20 webhook calls per minute per IP (PayMongo retries)
    "download": (30, 60 * 60),   # 30 downloads per hour per IP
    "status":   (120, 60),       # 120 status polls per minute per IP (polling every 5s)
}


def _get_client_ip(request: Request) -> str:
    # Render passes real IP in X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str, category: str):
    """
    Sliding window rate limiter.
    Raises HTTP 429 if the IP exceeds the limit for this category.
    """
    max_req, window = RATE_LIMITS[category]
    key = f"{category}:{ip}"
    now = time.time()

    with _rate_lock:
        timestamps = _rate_data[key]
        # Purge timestamps outside the window
        _rate_data[key] = [t for t in timestamps if now - t < window]
        if len(_rate_data[key]) >= max_req:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please wait before trying again.",
            )
        _rate_data[key].append(now)


def _clean_rate_data():
    """
    Prune stale rate limit entries to avoid unbounded memory growth.
    Call this periodically — here we piggyback on _cleanup_expired().
    """
    now = time.time()
    with _rate_lock:
        stale = [
            k for k, ts in _rate_data.items()
            if not ts or now - max(ts) > 3600
        ]
        for k in stale:
            del _rate_data[k]


# ── Store helpers ──────────────────────────────────────────────────────────────
def _load_jobs():
    global _jobs
    try:
        if os.path.exists(_JOBS_FILE):
            with open(_JOBS_FILE, "r") as f:
                data = json.load(f)
            cutoff = time.time() - 7200
            _jobs = {k: v for k, v in data.items() if v.get("created_at", 0) > cutoff}
            print(f"🗂️  Jobs store loaded: {len(_jobs)} active job(s)")
    except Exception as e:
        print(f"⚠️  Could not load jobs store: {e}")
        _jobs = {}


def _save_jobs():
    try:
        with open(_JOBS_FILE, "w") as f:
            json.dump(_jobs, f)
    except Exception as e:
        print(f"⚠️  Could not save jobs store: {e}")


def _prune_jobs():
    """Remove jobs older than 2 hours from memory (not just on startup)."""
    cutoff = time.time() - 7200
    with _jobs_lock:
        stale = [k for k, v in _jobs.items() if v.get("created_at", 0) < cutoff]
        for k in stale:
            _jobs.pop(k, None)
        if stale:
            _save_jobs()
            print(f"🧹 Pruned {len(stale)} stale job(s)")


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
    _clean_rate_data()
    _prune_jobs()
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
_load_jobs()


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


# ── FIX 1: Webhook signature verification ────────────────────────────────────
def _verify_paymongo_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    PayMongo signs webhooks using HMAC-SHA256.
    Header format: "t=<timestamp>,te=<hmac>,li=<hmac>"
    We verify the 'te' (test) or 'li' (live) HMAC against our webhook secret.

    Get your webhook secret from:
    PayMongo Dashboard → Developers → Webhooks → [your webhook] → Secret key
    Store it as PAYMONGO_WEBHOOK_SECRET in your Render environment variables.
    """
    if not PAYMONGO_WEBHOOK_SECRET:
        # If secret not configured, block all webhooks — safer than allowing all
        print("⚠️  PAYMONGO_WEBHOOK_SECRET not set — rejecting webhook")
        return False

    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(",") if "=" in p)
        timestamp = parts.get("t", "")
        # PayMongo uses 'li' for live, 'te' for test
        signature = parts.get("li") or parts.get("te", "")

        if not timestamp or not signature:
            return False

        # Reconstruct the signed payload: timestamp + "." + raw_body
        signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
        expected = hmac.new(
            PAYMONGO_WEBHOOK_SECRET.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
    except Exception as e:
        print(f"⚠️  Signature verification error: {e}")
        return False


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


# ── FIX 2: Background generation with executor for blocking PPTX build ────────
async def _run_generation(ref: str, job: Dict):
    """
    Runs AI generation + file building for a paid job.
    pptx/pdf builds are offloaded to a thread pool via run_in_executor
    so they don't block FastAPI's async event loop.
    """
    pptx_path = None
    pdf_path  = None
    loop = asyncio.get_event_loop()

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

        # Offload synchronous CPU-bound builds to thread pool
        pptx_path = await loop.run_in_executor(
            None,
            lambda: build_presentation(
                slides=slides, title=job["title"], subject=job["subject"],
                level=job["level"], language=job["language"],
            )
        )

        if job.get("want_pdf"):
            pdf_path = await loop.run_in_executor(
                None,
                lambda: build_presenter_pdf(
                    slides=slides, title=job["title"], subject=job["subject"],
                    level=job["level"], language=job["language"],
                )
            )

        token = _save_token(pptx_path, pdf_path, _safe_title(job["title"]))

        with _jobs_lock:
            _jobs[ref].update({
                "status":  "ready",
                "token":   token,
                "has_pdf": pdf_path is not None,
            })
            _save_jobs()
        print(f"✅ Generation done for ref {ref}")

    except Exception as e:
        print(f"❌ Generation error for ref {ref}: {e}")
        _cleanup_paths(pptx_path, pdf_path)
        with _jobs_lock:
            _jobs[ref]["status"] = "failed"
            _save_jobs()


# ── POST /api/create-payment ───────────────────────────────────────────────────
@router.post("/create-payment")
async def create_payment(req: CreatePaymentRequest, request: Request):
    # FIX: Rate limit payment creation by IP
    _check_rate_limit(_get_client_ip(request), "payment")

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
        _save_jobs()

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
    URL:    https://your-backend.onrender.com/api/webhook
    Events: checkout_session.payment.paid

    REQUIRED env var on Render: PAYMONGO_WEBHOOK_SECRET
    Get it from: PayMongo Dashboard → Developers → Webhooks → your webhook → Secret key
    """
    # FIX: Rate limit webhook calls
    _check_rate_limit(_get_client_ip(request), "webhook")

    # FIX: Verify PayMongo signature BEFORE processing anything
    raw_body = await request.body()
    signature_header = request.headers.get("X-Paymongo-Signature", "")

    if not _verify_paymongo_signature(raw_body, signature_header):
        print(f"⚠️  Webhook rejected — invalid or missing signature")
        # Return 200 anyway so PayMongo doesn't keep retrying a legitimately bad sig
        # but do NOT process the event
        return {"received": True}

    try:
        body       = json.loads(raw_body)
        event_type = body.get("data", {}).get("attributes", {}).get("type", "")

        if event_type not in ("checkout_session.payment.paid", "payment.paid"):
            return {"received": True}

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

    return {"received": True}


# ── GET /api/payment-status/{ref} ─────────────────────────────────────────────
@router.get("/payment-status/{ref}")
def payment_status(ref: str, request: Request):
    # Rate limit polling — frontend polls every 5s, 120/min is very generous
    _check_rate_limit(_get_client_ip(request), "status")

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


# ── FIX 3: Legacy routes — disabled on production ─────────────────────────────
# These endpoints have NO payment check. They must NEVER be reachable in prod.
# To use locally: add ENABLE_LEGACY_ROUTES=true to backend/.env
# On Render: do NOT add this env var (defaults to false = blocked).

@router.post("/generate")
async def generate_presentation(req: GenerateRequest):
    if not _LEGACY_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is disabled in production. Use /api/create-payment."
        )
    pptx_path = None
    try:
        slides = await generate_slide_content(
            subject=req.subject, level=req.level, title=req.title,
            language=req.language, instructions=req.instructions,
        )
        loop = asyncio.get_event_loop()
        pptx_path = await loop.run_in_executor(
            None,
            lambda: build_presentation(
                slides=slides, title=req.title, subject=req.subject,
                level=req.level, language=req.language,
            )
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


@router.post("/generate/both")
async def generate_both(req: GenerateRequest):
    if not _LEGACY_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is disabled in production. Use /api/create-payment."
        )
    pptx_path = None
    pdf_path  = None
    try:
        slides = await generate_slide_content(
            subject=req.subject, level=req.level, title=req.title,
            language=req.language, instructions=req.instructions,
        )
        loop = asyncio.get_event_loop()
        pptx_path = await loop.run_in_executor(
            None,
            lambda: build_presentation(
                slides=slides, title=req.title, subject=req.subject,
                level=req.level, language=req.language,
            )
        )
        pdf_path = await loop.run_in_executor(
            None,
            lambda: build_presenter_pdf(
                slides=slides, title=job["title"], subject=job["subject"],
                level=job["level"], language=job["language"],
            )
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
def download_pptx(token: str, request: Request):
    _check_rate_limit(_get_client_ip(request), "download")
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
def download_pdf(token: str, request: Request):
    _check_rate_limit(_get_client_ip(request), "download")
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
        "api_configured":      bool(key),
        "payment_configured":  bool(PAYMONGO_SECRET),
        "webhook_configured":  bool(PAYMONGO_WEBHOOK_SECRET),
        "legacy_routes_enabled": _LEGACY_ENABLED,
        "status": "ready" if key else "missing_api_key",
    }
