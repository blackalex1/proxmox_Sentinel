import pytest
import asyncio
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch

from modules.proxmox.monitor.hysteria_alerts import (
    process_hysteria_audit_event,
    active_activity_cards,
    check_and_send_card_delayed,
    is_card_active
)
from core.outbox import ResilientOutbox, OUTBOX_FILE


@pytest.fixture(autouse=True)
def clean_state():
    """Очищаем состояние карточек и очереди перед каждым тестом."""
    active_activity_cards.clear()
    import os
    if os.path.exists(OUTBOX_FILE):
        try:
            os.remove(OUTBOX_FILE)
        except Exception:
            pass
    yield
    active_activity_cards.clear()
    if os.path.exists(OUTBOX_FILE):
        try:
            os.remove(OUTBOX_FILE)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_singbox_client_burst_connections_single_card():
    """
    Симуляция логики ядра Sing-box при множественных подключениях:
    Клиент 'test_client_a' открывает 30 соединений подряд (браузер, мессенджер, keepalive).
    Проверяем:
    - Создается ровно 1 карточка в памяти активных сессий.
    - Все события дописываются в хронологию одной карточки.
    - Нет спама новыми карточками.
    """
    mock_panel = AsyncMock()
    mock_panel.name = "Test-Node-1"

    sent_messages = []
    edited_messages = []

    async def mock_send_rich(chat_id, text, **kwargs):
        msg = MagicMock()
        msg.message_id = 1001
        msg.text = text
        sent_messages.append({"chat_id": chat_id, "text": text, "message_id": msg.message_id})
        return msg

    async def mock_edit_rich(chat_id, message_id, text, **kwargs):
        edited_messages.append({"chat_id": chat_id, "message_id": message_id, "text": text})
        return True

    now = time.time()
    mock_session_row = {"connect_time": "2026-06-15 12:00:00", "disconnect_time": None, "download_bytes": 0, "upload_bytes": 0}

    with patch("asyncio.sleep", AsyncMock()), \
         patch("core.config.settings.admin_ids", [123456789]), \
         patch("core.db.execute_read_one", AsyncMock(return_value=mock_session_row)), \
         patch("core.db.save_vpn_connect", AsyncMock(return_value="sess_test_001")), \
         patch("modules.proxmox.monitor.hysteria_alerts.check_new_ip_and_get_history", AsyncMock(return_value=(False, []))), \
         patch("modules.proxmox.monitor.hysteria_alerts.get_traffic_from_api", AsyncMock(return_value=(100000, 200000))), \
         patch("modules.proxmox.monitor.utils.send_rich_message", side_effect=mock_send_rich), \
         patch("modules.proxmox.monitor.utils.edit_rich_message", side_effect=mock_edit_rich):

        # Симулируем 30 событий singbox_connect от test_client_a (тестовый IP 198.51.100.10)
        for i in range(30):
            details_payload = json.dumps({"username": "test_client_a", "duration": "0 сек"})
            await process_hysteria_audit_event(
                panel=mock_panel,
                action="singbox_connect",
                client_ip="198.51.100.10",
                log_timestamp=now + i * 2,
                details_str=details_payload
            )

        # Вызываем отправку задержанной карточки
        key = ("Test-Node-1", "test_client_a", "Sing-box")
        assert key in active_activity_cards
        await check_and_send_card_delayed(key, "sess_test_001")

        # Проверяем: отправлено РОВНО 1 новое сообщение
        assert len(sent_messages) == 1
        card = active_activity_cards[key]
        assert card["pending_send"] is False
        assert len(card["admin_messages"]) == 1
        assert card["admin_messages"][0]["message_id"] == 1001


@pytest.mark.asyncio
async def test_cores_under_telegram_flood_wait_outbox_deduplication():
    """
    Симуляция высокой нагрузки при Flood Wait от Telegram:
    1. Telegram возвращает 429 Flood Wait (отправка возвращает None и перенаправляет в Outbox).
    2. Три тестовых клиента (test_client_a, test_client_b, test_client_c) генерируют поток событий Sing-box и Hysteria.
    Проверяем:
    - Очередь Outbox НЕ раздувается (сохраняется ровно по 1 карточке на каждого клиента).
    - Карточки в памяти остаются активными и накапливают события в единую хронологию.
    - После восстановления из Outbox отправляется ровно 3 компактных сообщения, а не десятки дубликатов.
    """
    mock_panel = AsyncMock()
    mock_panel.name = "Test-Node-1"

    outbox = ResilientOutbox()
    
    async def mock_send_rich_throttled(chat_id, text, **kwargs):
        await outbox.add_message(chat_id, text, **kwargs)
        return None

    now = time.time()
    mock_session_row = {"connect_time": "2026-06-15 12:00:00", "disconnect_time": None, "download_bytes": 0, "upload_bytes": 0}

    with patch("asyncio.sleep", AsyncMock()), \
         patch("core.config.settings.admin_ids", [123456789]), \
         patch("core.db.execute_read_one", AsyncMock(return_value=mock_session_row)), \
         patch("core.db.save_vpn_connect", AsyncMock(side_effect=lambda u, ip, *a, **k: f"sess_{u}_{ip}")), \
         patch("modules.proxmox.monitor.hysteria_alerts.check_new_ip_and_get_history", AsyncMock(return_value=(False, []))), \
         patch("modules.proxmox.monitor.hysteria_alerts.get_traffic_from_api", AsyncMock(return_value=(1000, 2000))), \
         patch("modules.proxmox.monitor.utils.send_rich_message", side_effect=mock_send_rich_throttled):

        clients = [
            ("test_client_a", "198.51.100.10", "singbox_connect", "Sing-box"),
            ("test_client_b", "198.51.100.20", "singbox_connect", "Sing-box"),
            ("test_client_c", "203.0.113.30", "hysteria2_connect", "Hysteria 2"),
        ]

        # Симулируем 60 входящих событий (по 20 на каждого клиента вперемешку)
        for cycle in range(20):
            for username, ip, action, proto in clients:
                details = json.dumps({"username": username, "duration": "0 сек"})
                await process_hysteria_audit_event(
                    panel=mock_panel,
                    action=action,
                    client_ip=ip,
                    log_timestamp=now + cycle * 5,
                    details_str=details
                )
                
                key = (mock_panel.name, username, proto)
                await check_and_send_card_delayed(key, f"sess_{username}_{ip}")

        # ПРОВЕРКА 1: Карточки в памяти остались активными благодаря флагу in_outbox
        for username, ip, action, proto in clients:
            key = (mock_panel.name, username, proto)
            assert key in active_activity_cards
            card = active_activity_cards[key]
            assert is_card_active(card, now + 100) is True
            assert card.get("in_outbox") is True

        # ПРОВЕРКА 2: В очереди Outbox строго 3 сообщения (по 1 на каждого клиента), а не 60!
        assert len(outbox.queue) == 3

        # ПРОВЕРКА 3: Проверяем, что в очереди лежат сообщения именно для наших 3 тестовых пользователей
        queued_texts = [msg["text"] for msg in outbox.queue]
        assert any("<code>test_client_a</code>" in t for t in queued_texts)
        assert any("<code>test_client_b</code>" in t for t in queued_texts)
        assert any("<code>test_client_c</code>" in t for t in queued_texts)

        # ПРОВЕРКА 4: Симулируем сброс очереди в Telegram после снятия кулдауна
        bot = MagicMock()
        delivered_messages = []
        async def mock_bot_send(chat_id, text, **kwargs):
            delivered_messages.append({"chat_id": chat_id, "text": text})
            return True

        bot._original_send_message = AsyncMock(side_effect=mock_bot_send)
        await outbox.flush_queue(bot)

        # Доставлено ровно 3 сообщения, очередь полностью очищена
        assert len(delivered_messages) == 3
        assert len(outbox.queue) == 0


@pytest.mark.asyncio
async def test_noise_disconnect_filtered_no_card_spam():
    """
    Симуляция коротких шумовых сессий (duration <= 3 сек, 0 байт трафика):
    Проверяем, что шумовые сессии Sing-box/Hysteria отсекаются и не создают карточек.
    """
    mock_panel = AsyncMock()
    mock_panel.name = "Test-Node-1"

    now = time.time()
    noise_res = ("sess_noise", 2, 0, 0)

    with patch("asyncio.sleep", AsyncMock()), \
         patch("core.config.settings.admin_ids", [123456789]), \
         patch("core.db.save_vpn_disconnect", AsyncMock(return_value=noise_res)), \
         patch("modules.proxmox.monitor.utils.send_rich_message", AsyncMock()) as mock_send:

        details = json.dumps({"username": "noise_user_test", "duration": "2 сек", "tx": 0, "rx": 0})
        await process_hysteria_audit_event(
            panel=mock_panel,
            action="singbox_disconnect",
            client_ip="192.0.2.99",
            log_timestamp=now,
            details_str=details
        )

        mock_send.assert_not_called()
        key = (mock_panel.name, "noise_user_test", "Sing-box")
        assert key not in active_activity_cards
