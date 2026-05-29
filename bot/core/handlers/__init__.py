from aiogram import Router
from .base import router as base_router
from .status import router as status_router
from .history import router as history_router
from .ban_center import router as ban_center_router

router = Router(name="core_router")
router.include_router(base_router)
router.include_router(status_router)
router.include_router(history_router)
router.include_router(ban_center_router)
