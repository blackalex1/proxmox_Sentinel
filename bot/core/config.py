import os
from dotenv import load_dotenv

# Определяем базовую директорию проекта (папка bot/)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, 'config', '.env')

# Загружаем переменные из папки config/.env
load_dotenv(env_path)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN or BOT_TOKEN == 'your_telegram_bot_token_here':
    raise ValueError("Пожалуйста, укажите валидный BOT_TOKEN в файле .env")

# Парсим ID админов
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(',') if x.strip().isdigit()]

# Proxmox настройки
PROXMOX_HOST = os.getenv('PROXMOX_HOST')
PROXMOX_USER = os.getenv('PROXMOX_USER')
PROXMOX_TOKEN_ID = os.getenv('PROXMOX_TOKEN_ID')
PROXMOX_TOKEN_SECRET = os.getenv('PROXMOX_TOKEN_SECRET')
PROXMOX_VERIFY_SSL = os.getenv('PROXMOX_VERIFY_SSL', 'False').lower() in ('true', '1', 'y', 'yes')

# 3X-UI настройки
XUI_HOST = os.getenv('XUI_HOST', '')
XUI_USERNAME = os.getenv('XUI_USERNAME', '')
XUI_PASSWORD = os.getenv('XUI_PASSWORD', '')
XUI_API_TOKEN = os.getenv('XUI_API_TOKEN', '')

# Ansible настройки
ANSIBLE_PLAYBOOKS_DIR = os.getenv('ANSIBLE_PLAYBOOKS_DIR', '')
if not ANSIBLE_PLAYBOOKS_DIR:
    ANSIBLE_PLAYBOOKS_DIR = os.path.join(os.getcwd(), 'playbooks')

# Прокси соединения для Telegram (http:// или socks5://)
PROXY_URL = os.getenv('PROXY_URL', '')

# Доверенные IP-адреса администраторов (через запятую) для бесшумного доступа к портам управления 8006/22
TRUSTED_ADMIN_IPS_STR = os.getenv('TRUSTED_ADMIN_IPS', '')
TRUSTED_ADMIN_IPS = [ip.strip() for ip in TRUSTED_ADMIN_IPS_STR.split(',') if ip.strip()]

# LXC Мониторинг настройки
MONITOR_LXC_CPU = int(os.getenv('MONITOR_LXC_CPU', '90'))
MONITOR_LXC_RAM = int(os.getenv('MONITOR_LXC_RAM', '90'))
MONITOR_LXC_DISK = int(os.getenv('MONITOR_LXC_DISK', '90'))

MONITOR_LXC_PORTS_WHITELIST = [int(p.strip()) for p in os.getenv('MONITOR_LXC_PORTS_WHITELIST', '80,443,53,123').split(',') if p.strip().isdigit()]
MONITOR_LXC_PORTS_SENSITIVE = [int(p.strip()) for p in os.getenv('MONITOR_LXC_PORTS_SENSITIVE', '22,3389,3306,5432,27017,8006').split(',') if p.strip().isdigit()]

# VPN настройки
VPN_VMID = int(os.getenv('VPN_VMID', '101'))
MONITOR_LXC_VPN_PORTS = [int(p.strip()) for p in os.getenv('MONITOR_LXC_VPN_PORTS', '51820,1194').split(',') if p.strip().isdigit()]

# Дополнительные настройки уведомлений VPN
VPN_OFFLINE_TIMEOUT = int(os.getenv('VPN_OFFLINE_TIMEOUT', '1800'))
VPN_IGNORE_USERS = [u.strip() for u in os.getenv('VPN_IGNORE_USERS', '').split(',') if u.strip()]
ALERT_VPN_CLIENT_UNUSUAL_PORTS = os.getenv('ALERT_VPN_CLIENT_UNUSUAL_PORTS', 'False').lower() in ('true', '1', 'y', 'yes')

# Мониторинг удаленного сервера (Target VPS)
REMOTE_MONITOR_ENABLE = os.getenv('REMOTE_MONITOR_ENABLE', 'False').lower() in ('true', '1', 'y', 'yes')

REMOTE_IPS_STR = os.getenv('REMOTE_SERVER_IP', '')
REMOTE_USERS_STR = os.getenv('REMOTE_SERVER_USER', 'root')
REMOTE_KEYS_STR = os.getenv('REMOTE_SERVER_SSH_KEY', 'config/id_rsa_remote')

REMOTE_IPS = [ip.strip() for ip in REMOTE_IPS_STR.split(',') if ip.strip()]
REMOTE_USERS = [u.strip() for u in REMOTE_USERS_STR.split(',') if u.strip()]
REMOTE_KEYS = [k.strip() for k in REMOTE_KEYS_STR.split(',') if k.strip()]

# Выравниваем списки по количеству IP-адресов
while len(REMOTE_USERS) < len(REMOTE_IPS):
    REMOTE_USERS.append('root')
while len(REMOTE_KEYS) < len(REMOTE_IPS):
    REMOTE_KEYS.append('config/id_rsa_remote')

REMOTE_SERVERS = []
for ip, user, key_path in zip(REMOTE_IPS, REMOTE_USERS, REMOTE_KEYS):
    if key_path and not os.path.isabs(key_path):
        candidate = os.path.abspath(os.path.join(base_dir, key_path))
        if not os.path.exists(candidate):
            config_candidate = os.path.abspath(os.path.join(base_dir, 'config', key_path))
            if os.path.exists(config_candidate):
                candidate = config_candidate
        key_path = candidate
    
    # Автоматически устанавливаем безопасные права (600) для SSH-ключа на Linux
    if key_path and os.name != 'nt' and os.path.exists(key_path):
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
            
    REMOTE_SERVERS.append({
        'ip': ip,
        'user': user,
        'key': key_path
    })

# Экспортируем одиночные переменные для обратной совместимости
REMOTE_SERVER_IP = REMOTE_IPS[0] if REMOTE_IPS else ''
REMOTE_SERVER_USER = REMOTE_USERS[0] if REMOTE_USERS else 'root'
REMOTE_SERVER_SSH_KEY = REMOTE_SERVERS[0]['key'] if REMOTE_SERVERS else ''




