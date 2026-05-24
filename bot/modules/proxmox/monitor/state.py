from collections import deque, defaultdict

# Глобальные rolling-буферы для хранения истории в оперативной памяти
lxc_auth_history = defaultdict(lambda: deque(maxlen=100))
lxc_traffic_history = defaultdict(lambda: deque(maxlen=100))

# Кэши для быстрого поиска метаданных без спама в Proxmox API
lxc_name_cache = {0: "Хост Proxmox VE"}        # vmid -> name
lxc_state_cache = {0: "running"}       # vmid -> state (running/stopped)
lxc_alert_throttle = {}    # (vmid, metric) -> timestamp or (vmid, 'threat', label, dst, dpt) -> timestamp

# Список активных наблюдателей за авторизациями
# vmid -> LogTailer instance
auth_tailers = {}

# Наблюдатель за трафиком
traffic_tailer = None

# Rolling буфер для дедупликации локальных соединений VPN-контейнера
recent_local_conns = deque(maxlen=500)
