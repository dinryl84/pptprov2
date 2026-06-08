from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.generate import router as generate_router
from routes.generate_lesson import router as lesson_router   # ← NEW
import os

app = FastAPI(title="pptPro API", version="2.2.0")

# ── CORS ───────────────────────────────────────────────────────────────────────
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://pptprov2.vercel.app")

ALLOWED_ORIGINS = [
    _FRONTEND_URL,
    "https://pptprov2.vercel.app",
    # ── LessonPro frontend (update this when you host LessonPro) ──
    # If you host LessonPro on Vercel, add its URL here.
    # For now, file:// local use is handled by allowing * in dev mode.
]

# Add localhost for local development
if os.environ.get("ENVIRONMENT", "production") == "development":
    ALLOWED_ORIGINS += [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# ── LessonPro frontend (locked to Vercel URL) ─────────────────────────────────
ALLOWED_ORIGINS.append("https://lessonpro.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(generate_router, prefix="/api")
app.include_router(lesson_router,   prefix="/api")   # ← NEW


@app.get("/")
def root():
    return {"message": "pptPro API v2.2 running 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}
