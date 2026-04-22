from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import time
import threading
import json

from services.ai_service import generate_slide_content
from services.pptx_service import build_presentation
from services.pdf_service import build_presenter_pdf

router = APIRouter()

TTL_SECONDS = 60 * 60  # 1 hour

# ── Disk-persisted token store ────────────────────────────────────────────────
# Survives server restarts. Falls back gracefully if file is missing/corrupt.
_STORE_FILE = os.path.join(
    os.environ.get("STORE_DIR", os.path.dirname(__file__)), ".token_store.json"
)
_store: Dict[str, Dict] = {}
_store_lock = threading.Lock()


def _load_store():
    """Load token store from disk on startup."""
    global _store
    try:
        if os.path.exists(_STORE_FILE):
            with open(_STORE_FILE, "r") as f:
                data = json.load(f)
            # Drop already-expired entries on load
            now = time.time()
            _store = {k: v for k, v in data.items() if v.get("expires", 0) > now}
            print(f"🗂️  Token store loaded: {len(_store)} active token(s)")
    except Exception as e:
        print(f"⚠️  Could not load token store: {e} — starting fresh")
        _store = {}


def _save_store():
    """Persist token store to disk. Called after every write."""
    try:
        with open(_STORE_FILE, "w") as f:
            json.dump(_store, f)
    except Exception as e:
        print(f"⚠️  Could not save token store: {e}")


def _cleanup_expired():
    """Remove expired entries and delete their files."""
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
    # Double-check the actual files still exist on disk
    pptx_ok = bool(entry.get("pptx_path") and os.path.exists(entry["pptx_path"]))
    if not pptx_ok:
        raise HTTPException(
            status_code=404,
            detail="Generated files were lost (likely a server restart). Please generate again."
        )
    return entry


# Load store immediately on module import (i.e., on server startup)
_load_store()


# ── Request models ─────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    subject: str
    level: str
    title: str
    language: str
    instructions: Optional[str] = ""


class TestGenerateRequest(BaseModel):
    subject: str
    level: str
    title: str
    language: str
    slides: List[Dict[str, Any]]


def _safe_title(title: str) -> str:
    return title.replace(" ", "_").replace("/", "-").replace("\\", "-")[:60]


def _cleanup_paths(*paths):
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass


# ── POST /generate ─────────────────────────────────────────────────────────────
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


# ── POST /generate/both ────────────────────────────────────────────────────────
@router.post("/generate/both")
async def generate_both(req: GenerateRequest):
    pptx_path = None
    pdf_path = None
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
    path = entry["pptx_path"]
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="PPTX file no longer available. Please generate again."
        )
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
    path = entry.get("pdf_path")
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="PDF file not available or already expired."
        )
    filename = f"{entry['filename_base']}_pptPro_Notes.pdf"
    return FileResponse(path=path, media_type="application/pdf", filename=filename)


# ── GET /status ────────────────────────────────────────────────────────────────
@router.get("/status")
def api_status():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    return {
        "api_configured": bool(key),
        "status": "ready" if key else "missing_api_key",
    }