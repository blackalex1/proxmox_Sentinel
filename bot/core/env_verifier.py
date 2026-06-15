import logging
from core.config import settings
from core.messages.i18n import _

def verify_env_configuration():
    """
    Проверяет настройки из файла .env и выводит в лог предупреждения
    о недостающих параметрах для полноценной работы всех систем.
    """
    missing = []
    
    # 1. Администраторы для получения алертов
    if not settings.admin_ids:
        missing.append(_("logs", "env_verifier_admin_ids"))
        
    # 2. Мониторинг Proxmox
    proxmox_fields = [settings.proxmox_host, settings.proxmox_user, settings.proxmox_token_id, settings.proxmox_token_secret]
    if not all(proxmox_fields):
        missing.append(_("logs", "env_verifier_proxmox"))
        
    # 4. Ansible Playbooks
    if not settings.ansible_playbooks_dir:
        missing.append(_("logs", "env_verifier_ansible"))
        
    # 5. Блокировки на роутере
    if not settings.router_monitor_enable:
        missing.append(_("logs", "env_verifier_router_enable"))
    elif not all([settings.router_ssh_host, settings.router_ssh_user]):
        missing.append(_("logs", "env_verifier_router_ssh"))
        
    # 6. Мониторинг удаленных серверов (VPS)
    if not settings.remote_monitor_enable:
        missing.append(_("logs", "env_verifier_remote_enable"))
    elif not all([settings.remote_server_ip, settings.remote_server_user]):
        missing.append(_("logs", "env_verifier_remote_ssh"))
        
    # 7. Язык бота (BOT_LANGUAGE)
    if 'bot_language' not in settings.model_fields_set:
        missing.append(_("logs", "env_verifier_bot_language"))
        
    if missing:
        logging.warning("env_verifier_the_following_parameters_are_missing")
        for item in missing:
            logging.warning(f"  - {item}")
    else:
        logging.info("env_verifier_all_required_environment_variables_are")
