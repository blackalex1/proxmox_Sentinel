import asyncio
import logging
import ssl
from typing import Optional
from aiohttp import web
from core.config import settings
from .auth import deck_auth_and_security_middleware
from .crypto import get_strict_ssl_context
from .routes import setup_routes


_server_runner: Optional[web.AppRunner] = None
_server_site: Optional[web.TCPSite] = None


def create_deck_api_app() -> web.Application:
    """Создает приложение aiohttp с зарегистрированными middleware и роутами"""
    app = web.Application(middlewares=[deck_auth_and_security_middleware])
    setup_routes(app)
    return app


async def start_deck_api_server() -> None:
    """
    Точка входа для запуска строго защищенного HTTPS/WSS API-сервера Sentinel Deck.
    
    Принципы безопасности:
    1. Если enable_deck_api выключен в .env, сервер НЕ запускается и порт НЕ занимается.
    2. Требуется Bearer-токен длиной не менее 16 символов.
    3. Сервер работает ИСКЛЮЧИТЕЛЬНО по HTTPS / WSS:
       - Если сертификат не указан в .env, автоматически выпускается самоподписанный X.509
         сертификат на 10 лет с поддержкой локальных IP и доменов.
       - Любая попытка подключения по незашифрованному HTTP сбрасывается на уровне TLS-рукопожатия.
    """
    global _server_runner, _server_site

    if not getattr(settings, 'enable_deck_api', False):
        logging.debug("[Deck API] Plugin is disabled in .env (ENABLE_DECK_API=false). Server will not be started.")
        return

    token = getattr(settings, 'deck_api_token', '').strip()
    if not token or len(token) < 16:
        logging.error(
            "[Deck API Security] ENABLE_DECK_API is true, but DECK_API_TOKEN is empty or shorter than 16 characters! "
            "Server startup aborted for security reasons."
        )
        return

    host = getattr(settings, 'deck_api_host', '0.0.0.0')
    port = getattr(settings, 'deck_api_port', 8443)

    # 4. Инициализация строгого TLSv1.2+ контекста (автовыпуск сертификата при необходимости)
    try:
        ssl_ctx = get_strict_ssl_context()
    except Exception as ssl_err:
        logging.critical(
            f"[Deck API Security] FATAL: Cannot initialize HTTPS/WSS TLS context: {ssl_err}. "
            f"Plaintext fallback is forbidden."
        )
        return

    app = create_deck_api_app()
    _server_runner = web.AppRunner(app, access_log=None)
    await _server_runner.setup()

    _server_site = web.TCPSite(_server_runner, host=host, port=port, ssl_context=ssl_ctx)
    await _server_site.start()

    logging.info(
        f"🔒 [Deck API] STRICT HTTPS/WSS Server started and listening on https://{host}:{port} "
        f"(Self-signed TLSv1.2+ active, Bearer token auth, rate limit: {settings.deck_api_rate_limit} req/min)"
    )


async def stop_deck_api_server() -> None:
    """Корректное завершение работы сервера при остановке бота"""
    global _server_runner, _server_site
    if _server_site:
        await _server_site.stop()
        _server_site = None
    if _server_runner:
        await _server_runner.cleanup()
        _server_runner = None
    logging.info("[Deck API] HTTPS/WSS Server stopped cleanly.")
