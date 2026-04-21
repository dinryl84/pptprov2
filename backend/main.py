from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.generate import router as generate_router

app = FastAPI(title="pptPro API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "pptPro API v2 running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}
