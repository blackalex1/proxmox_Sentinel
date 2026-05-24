from aiogram import Router
from .nodes import router as nodes_router
from .vms import router as vms_router
from .clone import router as clone_router
from .logs import router as logs_router

router = Router(name="proxmox_router")
router.include_router(nodes_router)
router.include_router(vms_router)
router.include_router(clone_router)
router.include_router(logs_router)
