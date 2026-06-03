import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator

# Определяем базовую директорию проекта (папка bot/)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, 'config', '.env')

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding='utf-8',
        extra='ignore'
    )

    bot_token: str = Field(validation_alias='BOT_TOKEN')
    admin_ids: List[int] | str = Field(default_factory=list, validation_alias='ADMIN_IDS')

    # Proxmox настройки
    proxmox_host: str = Field(default='', validation_alias='PROXMOX_HOST')
    proxmox_user: str = Field(default='', validation_alias='PROXMOX_USER')
    proxmox_token_id: str = Field(default='', validation_alias='PROXMOX_TOKEN_ID')
    proxmox_token_secret: str = Field(default='', validation_alias='PROXMOX_TOKEN_SECRET')
    proxmox_verify_ssl: bool = Field(default=False, validation_alias='PROXMOX_VERIFY_SSL')

    # 3X-UI настройки
    xui_host: str = Field(default='', validation_alias='XUI_HOST')
    xui_username: str = Field(default='', validation_alias='XUI_USERNAME')
    xui_password: str = Field(default='', validation_alias='XUI_PASSWORD')
    xui_api_token: str = Field(default='', validation_alias='XUI_API_TOKEN')

    # Ansible настройки
    ansible_playbooks_dir: str = Field(default='', validation_alias='ANSIBLE_PLAYBOOKS_DIR')

    # Прокси соединения для Telegram (http:// или socks5://)
    proxy_url: str = Field(default='', validation_alias='PROXY_URL')

    # Альтернативный Bot API сервер (например, приватный реверс-прокси на Cloudflare Workers)
    telegram_api_server: str = Field(default='', validation_alias='TELEGRAM_API_SERVER')

    # Включение автоматической ротации бесплатных SOCKS5 прокси при сбое основного прокси
    enable_free_proxy_rotation: bool = Field(default=False, validation_alias='ENABLE_FREE_PROXY_ROTATION')

    # Доверенные IP-адреса администраторов
    trusted_admin_ips: List[str] | str = Field(default_factory=list, validation_alias='TRUSTED_ADMIN_IPS')

    # LXC Мониторинг настройки
    monitor_lxc_cpu: int = Field(default=90, validation_alias='MONITOR_LXC_CPU')
    monitor_lxc_ram: int = Field(default=90, validation_alias='MONITOR_LXC_RAM')
    monitor_lxc_disk: int = Field(default=90, validation_alias='MONITOR_LXC_DISK')

    monitor_lxc_ports_whitelist: List[int] | str = Field(default_factory=list, validation_alias='MONITOR_LXC_PORTS_WHITELIST')
    monitor_lxc_ports_sensitive: List[int] | str = Field(default_factory=list, validation_alias='MONITOR_LXC_PORTS_SENSITIVE')

    # VPN настройки
    vpn_vmid: int = Field(default=101, validation_alias='VPN_VMID')
    monitor_lxc_vpn_ports: List[int] | str = Field(default_factory=list, validation_alias='MONITOR_LXC_VPN_PORTS')

    # Дополнительные настройки уведомлений VPN
    vpn_offline_timeout: int = Field(default=1800, validation_alias='VPN_OFFLINE_TIMEOUT')
    vpn_ignore_users: List[str] | str = Field(default_factory=list, validation_alias='VPN_IGNORE_USERS')
    alert_vpn_client_unusual_ports: bool = Field(default=False, validation_alias='ALERT_VPN_CLIENT_UNUSUAL_PORTS')
    vpn_alert_debounce_sec: float = Field(default=3.0, validation_alias='VPN_ALERT_DEBOUNCE_SEC')

    # Мониторинг удаленного сервера (Target VPS)
    remote_monitor_enable: bool = Field(default=False, validation_alias='REMOTE_MONITOR_ENABLE')
    remote_monitor_ignore_keys: List[str] | str = Field(default=['bot@bot'], validation_alias='REMOTE_MONITOR_IGNORE_KEYS')
    remote_monitor_ignore_ips: List[str] | str = Field(default_factory=list, validation_alias='REMOTE_MONITOR_IGNORE_IPS')

    # Белый список процессов IPS
    ips_process_whitelist: List[str] | str = Field(default_factory=list, validation_alias='IPS_PROCESS_WHITELIST')

    # Белый список LXC контейнеров для IPS (им разрешены любые исходящие соединения)
    ips_lxc_whitelist: List[int] | str = Field(default_factory=list, validation_alias='IPS_LXC_WHITELIST')

    # Временный белый список командной строки процессов (для авто-тестов)
    ips_temp_whitelist_cmdline: str = Field(default='', validation_alias='IPS_TEMP_WHITELIST_CMDLINE')

    # Mihomo (Clash.Meta) мониторинг роутера
    mihomo_monitor_enable: bool = Field(default=False, validation_alias='MIHOMO_MONITOR_ENABLE')
    mihomo_api_host: str = Field(default='192.168.1.1', validation_alias='MIHOMO_API_HOST')
    mihomo_api_port: int = Field(default=9090, validation_alias='MIHOMO_API_PORT')
    mihomo_api_secret: str = Field(default='', validation_alias='MIHOMO_API_SECRET')
    mihomo_auto_ban: bool = Field(default=False, validation_alias='MIHOMO_AUTO_BAN')
    mihomo_max_violations: int = Field(default=3, validation_alias='MIHOMO_MAX_VIOLATIONS')
    mihomo_monitor_mode: str = Field(default='polling', validation_alias='MIHOMO_MONITOR_MODE')
    mihomo_poll_interval: float = Field(default=2.0, validation_alias='MIHOMO_POLL_INTERVAL')

    # Настройки SSH для роутера (для банов)
    router_ssh_enable: bool = Field(default=False, validation_alias='ROUTER_SSH_ENABLE')
    router_ssh_host: str = Field(default='192.168.1.1', validation_alias='ROUTER_SSH_HOST')
    router_ssh_port: int = Field(default=22, validation_alias='ROUTER_SSH_PORT')
    router_ssh_user: str = Field(default='root', validation_alias='ROUTER_SSH_USER')
    router_ssh_password: str = Field(default='', validation_alias='ROUTER_SSH_PASSWORD')
    router_ssh_key: str = Field(default='config/id_rsa_router', validation_alias='ROUTER_SSH_KEY')
    router_type: str = Field(default='openwrt', validation_alias='ROUTER_TYPE')

    # Параметры удаленных серверов
    remote_server_ip: str = Field(default='', validation_alias='REMOTE_SERVER_IP')
    remote_server_user: str = Field(default='root', validation_alias='REMOTE_SERVER_USER')
    remote_server_ssh_key: str = Field(default='config/id_rsa_remote', validation_alias='REMOTE_SERVER_SSH_KEY')

    # Сгенерированные сервера
    remote_servers: List[Dict[str, str]] = Field(default_factory=list)

    # Валидаторы полей
    @field_validator('bot_token')
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or v == 'your_telegram_bot_token_here':
            raise ValueError("Пожалуйста, укажите валидный BOT_TOKEN в файле .env")
        return v

    @field_validator(
        'admin_ids', 'monitor_lxc_ports_whitelist', 'monitor_lxc_ports_sensitive', 'monitor_lxc_vpn_ports', 'ips_lxc_whitelist',
        mode='before'
    )
    @classmethod
    def parse_int_list(cls, v: Any) -> List[int]:
        if isinstance(v, list):
            return [int(x) for x in v]
        if not v:
            return []
        return [int(x.strip()) for x in str(v).split(',') if x.strip().isdigit()]

    @field_validator(
        'trusted_admin_ips', 'vpn_ignore_users', 'ips_process_whitelist', 'remote_monitor_ignore_keys', 'remote_monitor_ignore_ips',
        mode='before'
    )
    @classmethod
    def parse_str_list(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v]
        if not v:
            return []
        return [x.strip() for x in str(v).split(',') if x.strip()]

    @property
    def mihomo_api_url(self) -> str:
        return f"http://{self.mihomo_api_host}:{self.mihomo_api_port}"

    # Пост-валидация для генерации структуры remote_servers
    @model_validator(mode='after')
    def build_remote_servers(self) -> 'Settings':
        ips = [ip.strip() for ip in self.remote_server_ip.split(',') if ip.strip()]
        users = [u.strip() for u in self.remote_server_user.split(',') if u.strip()]
        keys = [k.strip() for k in self.remote_server_ssh_key.split(',') if k.strip()]

        while len(users) < len(ips):
            users.append('root')
        while len(keys) < len(ips):
            keys.append('config/id_rsa_remote')

        servers = []
        for ip, user, key_path in zip(ips, users, keys):
            if key_path and not os.path.isabs(key_path):
                candidate = os.path.abspath(os.path.join(base_dir, key_path))
                if not os.path.exists(candidate):
                    config_candidate = os.path.abspath(os.path.join(base_dir, 'config', key_path))
                    if os.path.exists(config_candidate):
                        candidate = config_candidate
                key_path = candidate

            if key_path and os.name != 'nt' and os.path.exists(key_path):
                try:
                    os.chmod(key_path, 0o600)
                except Exception:
                    pass

            servers.append({
                'ip': ip,
                'user': user,
                'key': key_path
            })
        self.remote_servers = servers
        return self

# Инициализируем настройки
settings = Settings()
