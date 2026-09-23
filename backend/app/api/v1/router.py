"""Public API v1 router."""

from fastapi import APIRouter

from backend.app.api.v1.routes.router import router as routes_router

router = APIRouter(prefix="/api/v1")
router.include_router(routes_router)
