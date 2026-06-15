import logging
from core.config import settings

def verify_env_configuration():
    """
    Проверяет настройки из файла .env и выводит в лог предупреждения
    о недостающих параметрах для полноценной работы всех систем.
    """
    missing = []
    
    # 1. Администраторы для получения алертов
    if not settings.admin_ids:
        missing.append("ADMIN_IDS (получение алертов администраторами)")
        
    # 2. Мониторинг Proxmox
    proxmox_fields = [settings.proxmox_host, settings.proxmox_user, settings.proxmox_token_id, settings.proxmox_token_secret]
    if not all(proxmox_fields):
        missing.append("PROXMOX_* (PROXMOX_HOST, PROXMOX_USER, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET - мониторинг Proxmox VE)")
        
        
    # 4. Ansible Playbooks
    if not settings.ansible_playbooks_dir:
        missing.append("ANSIBLE_PLAYBOOKS_DIR (запуск плейбуков автоматизации)")
        
    # 5. Блокировки на роутере
    if not settings.router_monitor_enable:
        missing.append("ROUTER_MONITOR_ENABLE=True (блокировки вредоносного трафика на уровне роутера)")
    elif not all([settings.router_ssh_host, settings.router_ssh_user]):
        missing.append("ROUTER_SSH_* (ROUTER_SSH_HOST, ROUTER_SSH_USER - авторизация на роутере по SSH)")
        
    # 6. Мониторинг удаленных серверов (VPS)
    if not settings.remote_monitor_enable:
        missing.append("REMOTE_MONITOR_ENABLE=True (мониторинг и защита удаленных VPS)")
    elif not all([settings.remote_server_ip, settings.remote_server_user]):
        missing.append("REMOTE_SERVER_* (REMOTE_SERVER_IP, REMOTE_SERVER_USER - SSH доступ к удаленным серверам)")
        
    if missing:
        logging.warning("env_verifier_the_following_parameters_are_missing")
        for item in missing:
            logging.warning(f"  - {item}")
    else:
        logging.info("env_verifier_all_required_environment_variables_are")
