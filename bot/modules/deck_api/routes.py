import json
import logging
import time
from typing import Any, Dict
from aiohttp import web
from core.config import settings
from .broadcaster import deck_broadcaster
from .auth import extract_token_from_request, verify_bearer_token


async def handle_health(request: web.Request) -> web.Response:
    """Проверка доступности сервиса"""
    return web.json_response({
        "status": "ok",
        "service": "Proxmox Sentinel (PVE Aegis)",
        "version": "1.0.0",
        "timestamp": time.time(),
        "connected_clients": deck_broadcaster.client_count
    })


async def handle_get_alerts(request: web.Request) -> web.Response:
    """Получение недавних алертов из памяти"""
    return web.json_response({
        "alerts": deck_broadcaster.get_recent_alerts(),
        "total": len(deck_broadcaster.get_recent_alerts()),
        "timestamp": time.time()
    })


async def handle_get_nodes(request: web.Request) -> web.Response:
    """Безопасный опрос статуса нод Proxmox"""
    try:
        from modules.proxmox.api import proxmox
        nodes = proxmox.get_nodes() if proxmox else []
        return web.json_response({
            "nodes": nodes,
            "timestamp": time.time()
        })
    except Exception as e:
        logging.error(f"[Deck API] Failed to fetch Proxmox nodes: {e}")
        return web.json_response({
            "nodes": [],
            "error": "Failed to fetch nodes from Proxmox API",
            "timestamp": time.time()
        }, status=500)


async def handle_ws_stream(request: web.Request) -> web.WebSocketResponse:
    """
    Потоковый WebSocket-эндпоинт для Sentinel Deck:
    - Потоковая передача алертов в реальном времени
    - Heartbeat для обнаружения обрыва связи
    """
    # 1. Проверка лимита одновременных подключений (защита от исчерпания дескрипторов сокетов)
    max_clients = getattr(settings, 'deck_api_max_clients', 5)
    if deck_broadcaster.client_count >= max_clients:
        logging.warning(f"[Deck API] Max clients limit reached ({max_clients}). Rejecting new WS connection.")
        return web.Response(
            status=503,
            text=json.dumps({"error": "Service Unavailable", "detail": "Max concurrent clients reached."}),
            content_type="application/json"
        )

    # 2. Инициализация WebSocket с лимитом размера сообщений и пинг-понгом
    ws = web.WebSocketResponse(
        heartbeat=20.0,
        max_msg_size=65536  # Ограничение 64 КБ на сообщение для предотвращения переполнения буфера
    )
    await ws.prepare(request)

    await deck_broadcaster.register(ws)

    try:
        # Отправляем клиенту начальное приветствие и снимок текущих алертов
        init_payload = {
            "type": "init",
            "service": "Proxmox Sentinel",
            "timestamp": time.time(),
            "recent_alerts": deck_broadcaster.get_recent_alerts()
        }
        await ws.send_json(init_payload)

        # Слушаем входящие сообщения от планшета (например, пинг или запрос алертов)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                    action = payload.get("action")
                    if action == "ping":
                        await ws.send_json({"type": "pong", "timestamp": time.time()})
                    elif action == "get_alerts":
                        await ws.send_json({
                            "type": "alerts_snapshot",
                            "alerts": deck_broadcaster.get_recent_alerts()
                        })
                except Exception as parse_err:
                    logging.debug(f"[Deck API WS] Malformed client message: {parse_err}")
            elif msg.type == web.WSMsgType.ERROR:
                logging.debug(f"[Deck API WS] Connection error: {ws.exception()}")
                break
    finally:
        await deck_broadcaster.unregister(ws)

    return ws


def setup_routes(app: web.Application) -> None:
    """Регистрация всех эндпоинтов Deck API"""
    app.router.add_get("/api/v1/health", handle_health)
    app.router.add_get("/api/v1/alerts", handle_get_alerts)
    app.router.add_get("/api/v1/nodes", handle_get_nodes)
    app.router.add_get("/api/v1/ws/stream", handle_ws_stream)
