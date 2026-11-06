import asyncio
import collections
import logging
import re
import time
from typing import Any, Dict, List, Optional
from aiohttp import web

# Регулярные выражения для санитизации логов и предотвращения утечек учетных данных
ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(bearer\s+)([A-Za-z0-9_\-\.]{10,})'), r'\1[REDACTED_TOKEN]'),
    (re.compile(r'(?i)(password\s*=\s*)([^\s;&]+)'), r'\1[REDACTED_PASSWORD]'),
    (re.compile(r'(?i)(bot_token\s*=\s*)([^\s;&]+)'), r'\1[REDACTED_BOT_TOKEN]'),
    (re.compile(r'(-----BEGIN [A-Z ]+ PRIVATE KEY-----)[\s\S]*?(-----END [A-Z ]+ PRIVATE KEY-----)'), r'\1\n[REDACTED_PRIVATE_KEY]\n\2'),
    (re.compile(r'(\b\d{9,11}:[A-Za-z0-9_-]{35}\b)'), r'[REDACTED_TELEGRAM_TOKEN]')
]


def sanitize_text(text: str) -> str:
    """Удаляет ANSI-последовательности терминала и маскирует токены/пароли/ключи."""
    if not text:
        return ""
    # Очистка ANSI цветов
    cleaned = ANSI_REGEX.sub('', text)
    # Маскирование секретов
    for pattern, repl in SENSITIVE_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()


class DeckBroadcaster:
    """
    Потокобезопасный брокер алертов для подключенных мобильных терминалов Sentinel Deck.
    Ограничивает использование памяти фиксированным кольцевым буфером (deque).
    """
    def __init__(self, max_alerts: int = 100):
        self._active_clients: set[web.WebSocketResponse] = set()
        self._alerts_history: collections.deque = collections.deque(maxlen=max_alerts)
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._active_clients)

    async def register(self, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            self._active_clients.add(ws)
            logging.info(f"[Deck API] Client connected. Total active clients: {len(self._active_clients)}")

    async def unregister(self, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            self._active_clients.discard(ws)
            logging.info(f"[Deck API] Client disconnected. Total active clients: {len(self._active_clients)}")

    def get_recent_alerts(self) -> List[Dict[str, Any]]:
        return list(self._alerts_history)

    async def broadcast_alert(
        self,
        raw_text: Any,
        parse_mode: str = "HTML",
        severity: str = "WARNING",
        category: str = "SECURITY",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Публикует новый алерт всем подключенным клиентам Sentinel Deck.
        """
        text_str = str(raw_text) if raw_text is not None else ""
        clean_text = sanitize_text(text_str)
        if not clean_text:
            return

        # Интеллектуальное определение важности на основе контента, если не задана явно
        upper = clean_text.upper()
        if any(w in upper for w in ("КРИТИЧ", "CRITICAL", "ПАДЕНИЕ", "FAIL", "DOWN", "OFFLINE", "KILL", "УНИЧТОЖЕН", "БЛОКИРОВ")):
            detected_severity = "CRITICAL"
        elif any(w in upper for w in ("ВОССТАНОВ", "ONLINE", "SUCCESS", "УСПЕШ")):
            detected_severity = "INFO"
        else:
            detected_severity = severity

        alert_payload = {
            "type": "alert",
            "id": f"alert_{int(time.time() * 1000)}",
            "timestamp": time.time(),
            "severity": detected_severity,
            "category": category,
            "text": clean_text,
            "parse_mode": parse_mode,
            "metadata": metadata or {}
        }

        # Сохраняем в кольцевой буфер
        self._alerts_history.append(alert_payload)

        # Отправляем подключенным клиентам
        await self._broadcast_json(alert_payload)

    async def _broadcast_json(self, payload: Dict[str, Any]) -> None:
        if not self._active_clients:
            return

        dead_clients = []
        for ws in list(self._active_clients):
            try:
                if ws.closed:
                    dead_clients.append(ws)
                    continue
                await ws.send_json(payload)
            except Exception as e:
                logging.debug(f"[Deck API] Failed to send to client: {e}")
                dead_clients.append(ws)

        if dead_clients:
            async with self._lock:
                for ws in dead_clients:
                    self._active_clients.discard(ws)


# Глобальный инстанс брокера
deck_broadcaster = DeckBroadcaster()
