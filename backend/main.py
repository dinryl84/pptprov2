from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.generate import router as generate_router
import os

app = FastAPI(title="pptPro API", version="2.1.0")

# ── FIX: Restrict CORS to your Vercel frontend only ───────────────────────────
# Previously this was allow_origins=["*"] which let ANY website call your API.
# Now only your Vercel frontend (and localhost for dev) can make requests.
#
# If your Vercel URL changes, update FRONTEND_URL in Render env vars.
# Format: https://your-app.vercel.app (no trailing slash)

_FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://pptprov2.vercel.app")

ALLOWED_ORIGINS = [
    _FRONTEND_URL,
    # Allow Vercel preview deployments (branch deploys)
    # These match: https://pptprov2-git-main-yourusername.vercel.app
    "https://pptprov2.vercel.app",
]

# Add localhost for local development
if os.environ.get("ENVIRONMENT", "production") == "development":
    ALLOWED_ORIGINS += [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],   # Only what we actually use
    allow_headers=["Content-Type"],  # Only what we actually need
)

app.include_router(generate_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "pptPro API v2.1 running 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}
