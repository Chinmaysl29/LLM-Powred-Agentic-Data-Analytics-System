from fastapi import FastAPI

from backend.api.routes import router
from backend.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
