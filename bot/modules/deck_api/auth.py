import hmac
import logging
import time
from typing import Dict, List
from aiohttp import web
from core.config import settings


def verify_bearer_token(provided_token: str, expected_token: str) -> bool:
    """
    Безопасная проверка токена с защитой от атак по времени (timing attacks).
    """
    if not provided_token or not expected_token:
        return False
    return hmac.compare_digest(
        provided_token.strip().encode('utf-8'),
        expected_token.strip().encode('utf-8')
    )


class SlidingWindowRateLimiter:
    """
    Скользящее окно для ограничения частоты запросов с одного IP-адреса.
    Предотвращает брутфорс токенов и DoS-атаки на REST-эндпоинты.
    """
    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        # Очистка устаревших записей раз в 5 минут
        if now - self._last_cleanup > 300:
            self._cleanup(now)

        timestamps = self._requests.setdefault(ip, [])
        # Оставляем только таймстампы внутри текущего окна
        valid_from = now - self.window_seconds
        self._requests[ip] = [t for t in timestamps if t > valid_from]

        if len(self._requests[ip]) >= self.limit:
            return False

        self._requests[ip].append(now)
        return True

    def _cleanup(self, now: float) -> None:
        valid_from = now - self.window_seconds
        keys_to_delete = []
        for ip, times in self._requests.items():
            fresh = [t for t in times if t > valid_from]
            if fresh:
                self._requests[ip] = fresh
            else:
                keys_to_delete.append(ip)
        for ip in keys_to_delete:
            del self._requests[ip]
        self._last_cleanup = now


rate_limiter = SlidingWindowRateLimiter(
    limit=getattr(settings, 'deck_api_rate_limit', 60),
    window_seconds=60
)


def extract_token_from_request(request: web.Request) -> str:
    """Извлекает токен из заголовка Authorization: Bearer или query-параметра ?token="""
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    # Альтернатива для WebSocket-рукопожатий некоторых мобильных клиентов
    token_param = request.query.get("token", "").strip()
    if token_param:
        return token_param
    # Также проверяем Sec-WebSocket-Protocol
    ws_protocol = request.headers.get("Sec-WebSocket-Protocol", "").strip()
    if ws_protocol.startswith("token."):
        return ws_protocol.split("token.", 1)[1].strip()
    return ""


@web.middleware
async def deck_auth_and_security_middleware(request: web.Request, handler):
    """
    Глобальный middleware безопасности для REST API:
    - Проверка Bearer токена
    - Rate Limiting
    - Внедрение защитных заголовков (Secure Headers)
    """
    client_ip = request.remote or "unknown"

    # 1. Rate Limiting
    if not rate_limiter.is_allowed(client_ip):
        logging.warning(f"[Deck API Security] Rate limit exceeded for IP: {client_ip} on path {request.path}")
        return web.json_response(
            {"error": "Too Many Requests", "detail": "Rate limit exceeded. Please try again later."},
            status=429,
            headers={"Retry-After": "60"}
        )

    # 2. Bearer Token Verification
    expected_token = getattr(settings, 'deck_api_token', '')
    provided_token = extract_token_from_request(request)

    if not verify_bearer_token(provided_token, expected_token):
        logging.warning(f"[Deck API Security] Unauthorized access attempt from IP {client_ip} to {request.path}")
        return web.json_response(
            {"error": "Unauthorized", "detail": "Invalid or missing Bearer token."},
            status=401,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'}
        )

    # 3. Выполнение обработчика
    response = await handler(request)

    # 4. Добавление защитных HTTP заголовков
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response
