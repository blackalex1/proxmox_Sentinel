from aiogram import Router
from .inbounds import router as inbounds_router
from .clients import router as clients_router
from .fsm import router as fsm_router

router = Router(name="xui_router")
router.include_router(inbounds_router)
router.include_router(clients_router)
router.include_router(fsm_router)
