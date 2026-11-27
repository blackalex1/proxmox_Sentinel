from aiogram import Router
from .panel import router as panel_router, cmd_panel, cb_spectre_menu, cb_spectre_list, cb_add_slave, cb_add_master, cmd_setup_slave
from .system import router as system_router, cmd_backup, cb_backup, run_backup_for_panel, cmd_status_spectre, cb_status, run_status_for_panel, cmd_top_spectre, cmd_audit, cb_audit, run_audit_for_panel
from .clients import router as clients_router, generate_qr_code_png, cmd_my_spectre, cb_unban_tunnel, cmd_ban_client, cmd_unban_client, cb_tg_2fa_approve, cb_tg_2fa_block

router = Router(name="core_spectre_router")
router.include_router(panel_router)
router.include_router(system_router)
router.include_router(clients_router)
