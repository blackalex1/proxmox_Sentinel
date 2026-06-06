from aiogram import Router
from .base import router as base_router
from .status import router as status_router
from .history import router as history_router
from .ban_center import router as ban_center_router
from .spectre_handlers import router as spectre_router
from .whitelist import router as whitelist_router
from .threats import router as threats_router

router = Router(name="core_router")
router.include_router(base_router)
router.include_router(status_router)
router.include_router(history_router)
router.include_router(ban_center_router)
router.include_router(spectre_router)
router.include_router(whitelist_router)
router.include_router(threats_router)

