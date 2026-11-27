from collections import deque, defaultdict
from contextlib import asynccontextmanager
import time

# Общие runtime-буферы и троттлинг (без зависимостей от modules/)
lxc_alert_throttle = {}    # (vmid, metric) -> timestamp or (vmid, 'threat', label, dst, dpt) -> timestamp

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
    return is_proxy_selection_active or time.time() < proxy_selection_active_until


@asynccontextmanager
async def proxy_selection_scope(duration: float = 60.0):
    """Устанавливает временное окно игнорирования сетевых проверок на время подбора прокси."""
    global is_proxy_selection_active, proxy_selection_active_until
    is_proxy_selection_active = True
    proxy_selection_active_until = time.time() + duration
    try:
        yield
    finally:
        is_proxy_selection_active = False
        proxy_selection_active_until = 0.0
