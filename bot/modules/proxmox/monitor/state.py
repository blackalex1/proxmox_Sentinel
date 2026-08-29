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

# Rolling буфер для регистрации недавних исходящих портов самого бота (для мгновенного вайтлиста)
recent_bot_ports = deque(maxlen=200)

# Реестр активных проверок прокси: (host, port) -> count
active_proxy_checks = defaultdict(int)

# Временный набор IP-адресов, на которых сейчас активно выполняется ansible-playbook
active_ansible_targets = set()

# Флаг и таймстемп активного окна подбора/тестирования прокси ботом
is_proxy_selection_active = False
proxy_selection_active_until = 0.0

def is_proxy_selection_in_progress() -> bool:
    """Возвращает True, если бот прямо сейчас выполняет процедуру подбора/проверки прокси."""
    import time
    return is_proxy_selection_active or time.time() < proxy_selection_active_until

from contextlib import asynccontextmanager

@asynccontextmanager
async def proxy_selection_scope(duration: float = 60.0):
    """
    Асинхронный контекстный менеджер для установки временного окна игнорирования
    сетевых проверок на время активного подбора прокси ботом.
    """
    global is_proxy_selection_active, proxy_selection_active_until
    import time
    is_proxy_selection_active = True
    proxy_selection_active_until = time.time() + duration
    try:
        yield
    finally:
        is_proxy_selection_active = False
        proxy_selection_active_until = 0.0


