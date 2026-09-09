from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="VERIAUDIT API",
    description="Cross-lingual AI safety evaluation service. Demo mode is on by default.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"name": "VERIAUDIT API", "demo_mode": settings.demo_mode, "docs": "/docs"}
