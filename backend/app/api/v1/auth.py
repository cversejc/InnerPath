from fastapi import APIRouter

from app.api.v1.auth_account_routes import router as account_router
from app.api.v1.auth_session_routes import router as session_router


router = APIRouter()
router.include_router(account_router)
router.include_router(session_router)
