from collections import deque, defaultdict

from core.runtime_state import (
    lxc_alert_throttle,
    recent_bot_ports,
    active_proxy_checks,
    active_ansible_targets,
    is_proxy_selection_active,
    proxy_selection_active_until,
    is_proxy_selection_in_progress,
    proxy_selection_scope,
)

# Глобальные rolling-буферы для хранения истории LXC в оперативной памяти
lxc_auth_history = defaultdict(lambda: deque(maxlen=100))
lxc_traffic_history = defaultdict(lambda: deque(maxlen=100))

# Кэши для быстрого поиска метаданных без спама в Proxmox API
lxc_name_cache = {0: "Хост Proxmox VE"}        # vmid -> name
lxc_state_cache = {0: "running"}       # vmid -> state (running/stopped)

# Список активных наблюдателей за авторизациями (vmid -> LogTailer)
auth_tailers = {}

# Наблюдатель за трафиком
traffic_tailer = None

# Rolling буфер для дедупликации локальных соединений VPN-контейнера
recent_local_conns = deque(maxlen=500)
