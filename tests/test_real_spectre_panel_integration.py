import os
import sys
import time
import socket
import tempfile
import threading
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Динамически подключаем локальный репозиторий панели sentinel-panel к sys.path
PANEL_DIR = Path(__file__).resolve().parent.parent.parent / "panel"
if PANEL_DIR.exists() and str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))

from core.spectre_client import SpectrePanelInstance, SpectreClientManager, spectre_manager
from core.handlers.spectre.clients import cmd_ban_client, cmd_unban_client


def find_free_port() -> int:
    """Находит свободный локальный порт TCP для запуска сервера утилитой uvicorn."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_spectre_panel():
    """
    Модульная фикстура, которая инициализирует реальную БД SQLite панели Spectre Panel,
    заполняет её тестовыми клиентами и запускает НАСТОЯЩИЙ HTTP-сервер FastAPI (uvicorn)
    на свободном порту.
    """
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    temp_path = Path(temp_dir.name)
    db_file = temp_path / "integration_test_panel.db"
    
    # 1. Патчим конфигурацию панели перед импортом моделей и БД
    import backend.config
    backend.config.DB_PATH = db_file
    backend.config.settings.PANEL_PORT = find_free_port()
    backend.config.settings.PANEL_SECRET_PATH = "ui_integration"
    backend.config.settings.API_TOKEN = "real_integration_bearer_token_999"
    backend.config.settings.ADMIN_USERNAME = "admin_test"
    backend.config.settings.ADMIN_PASSWORD = "pass_test"

    # 2. Инициализируем структуру таблиц БД панели
    from backend.database import init_db, db_session
    from backend.models import ClientStats, Inbound
    init_db()

    # 3. Наполняем БД реальными инбаундами и клиентами
    with db_session() as session:
        inbound = Inbound(
            remark="VLESS Test Inbound",
            port=4433,
            protocol="vless",
            settings=json.dumps({
                "clients": [
                    {"email": "attacker@spectre.com", "id": "uuid-attacker-111", "enable": True},
                    {"email": "victim@spectre.com", "id": "uuid-victim-222", "enable": True}
                ]
            }),
            stream_settings="{}",
            sniffing="{}",
            enable=1
        )
        session.add(inbound)
        session.flush()

        client1 = ClientStats(
            email="attacker@spectre.com",
            client_uuid_or_pwd="uuid-attacker-111",
            enable=1,
            inbound_id=inbound.id,
            up=5000,
            down=20000
        )
        client2 = ClientStats(
            email="victim@spectre.com",
            client_uuid_or_pwd="uuid-victim-222",
            enable=1,
            inbound_id=inbound.id,
            up=100,
            down=500
        )
        session.add_all([client1, client2])
        session.commit()

    # 4. Запускаем локальный веб-сервер uvicorn в фоновом демоническом потоке
    from backend.main import app
    import uvicorn

    port = find_free_port()
    server_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(server_config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # 5. Ожидаем готовности сервера через отправку реальных HTTP-проб
    import urllib.request
    panel_url = f"http://127.0.0.1:{port}"
    ready = False
    for _ in range(30):
        try:
            req = urllib.request.Request(f"{panel_url}/api/security/search-client?key=attacker")
            req.add_header("Authorization", f"Bearer {backend.config.settings.API_TOKEN}")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)

    if not ready:
        pytest.fail(f"Не удалось запустить тестовый сервер Spectre Panel на {panel_url}")

    yield {
        "url": panel_url,
        "token": backend.config.settings.API_TOKEN,
        "secret": backend.config.settings.PANEL_SECRET_PATH,
        "db_path": db_file,
        "port": port
    }

    # Завершаем сервер
    server.should_exit = True
    temp_dir.cleanup()


@pytest.mark.asyncio
async def test_real_panel_client_search(live_spectre_panel):
    """
    Интеграционный тест: Поиск клиента бота на реальном HTTP-сервере Spectre Panel.
    Запрос уходит через aiohttp по реальному TCP-сокету к панели.
    """
    manager = SpectreClientManager()
    panel_instance = SpectrePanelInstance(
        name="Real-Panel-LXC",
        url=live_spectre_panel["url"],
        token=live_spectre_panel["token"],
        secret_path=live_spectre_panel["secret"],
        source_type="lxc",
        identifier="104"
    )
    manager.panels = {"lxc_104": panel_instance}

    clients = await manager.search_client_all("attacker@spectre.com")
    assert len(clients) == 1
    assert clients[0]["client"]["email"] == "attacker@spectre.com"
    assert clients[0]["panel_name"] == "Real-Panel-LXC"
    assert clients[0]["client"]["enable"] == 1


@pytest.mark.asyncio
async def test_real_panel_disable_and_enable_client(live_spectre_panel):
    """
    Интеграционный тест: Блокировка и разблокировка клиента бота на реальном HTTP-сервере Spectre Panel.
    Проверяет:
    1. Отправку реального POST /api/security/disable-client
    2. Изменение состояния в реальной SQLite БД панели
    3. Отправку реального POST /api/security/enable-client
    4. Восстановление состояния в БД панели
    """
    manager = SpectreClientManager()
    panel_instance = SpectrePanelInstance(
        name="Real-Panel-VPS",
        url=live_spectre_panel["url"],
        token=live_spectre_panel["token"],
        secret_path=live_spectre_panel["secret"],
        source_type="vps",
        identifier="194.87.29.14"
    )
    manager.panels = {"vps_194.87.29.14": panel_instance}

    # 1. Запрос на блокировку вредоносного клиента
    results_ban = await manager.disable_client_everywhere("attacker@spectre.com")
    assert len(results_ban) == 1
    panel_name, success, msg = results_ban[0]
    assert panel_name == "Real-Panel-VPS"
    assert success is True
    assert "blocked" in msg.lower() or "disabled" in msg.lower() or "terminated" in msg.lower()

    # 2. Проверяем состояние в БД панели напрямую
    from backend.database import db_session
    from backend.models import ClientStats
    with db_session() as session:
        client_db = session.query(ClientStats).filter_by(email="attacker@spectre.com").first()
        assert client_db is not None
        assert client_db.enable == 0
        assert client_db.block_reason == "IPS Auto-blocked"

    # 3. Запрос на разблокировку клиента
    results_unban = await manager.enable_client_everywhere("attacker@spectre.com")
    assert len(results_unban) == 1
    panel_name_unban, success_unban, msg_unban = results_unban[0]
    assert panel_name_unban == "Real-Panel-VPS"
    assert success_unban is True

    # 4. Проверяем восстановленное состояние в БД панели
    with db_session() as session:
        client_db_restored = session.query(ClientStats).filter_by(email="attacker@spectre.com").first()
        assert client_db_restored is not None
        assert client_db_restored.enable == 1
        assert client_db_restored.block_reason is None


@pytest.mark.asyncio
async def test_real_panel_audit_logs_retrieval(live_spectre_panel):
    """
    Интеграционный тест: Запрос реальных логов аудита безопасности с панели через HTTP GET /api/security/audit-logs.
    """
    panel_instance = SpectrePanelInstance(
        name="Real-Panel-Audit",
        url=live_spectre_panel["url"],
        token=live_spectre_panel["token"],
        secret_path=live_spectre_panel["secret"],
        source_type="lxc",
        identifier="104"
    )

    success, data = await panel_instance.get_audit_logs(limit=5)
    assert success is True
    assert "logs" in data or "success" in data or "items" in data


@pytest.mark.asyncio
async def test_real_panel_bot_ban_commands_e2e(live_spectre_panel):
    """
    E2E интеграционный тест: Вызов команд бота /ban и /unban против реального HTTP сервера Spectre Panel.
    """
    panel_instance = SpectrePanelInstance(
        name="LivePanel",
        url=live_spectre_panel["url"],
        token=live_spectre_panel["token"],
        secret_path=live_spectre_panel["secret"],
        source_type="lxc",
        identifier="104"
    )
    spectre_manager.panels = {"live_panel": panel_instance}

    # Имитируем сообщение Телеграм от админа для блокировки
    mock_status_msg = AsyncMock()
    mock_message_ban = AsyncMock()
    mock_message_ban.text = "/ban victim@spectre.com"
    mock_message_ban.reply = AsyncMock(return_value=mock_status_msg)

    await cmd_ban_client(mock_message_ban)

    mock_message_ban.reply.assert_called_once()
    mock_status_msg.edit_text.assert_called_once()
    ban_reply_text = mock_status_msg.edit_text.call_args[0][0]
    assert "victim@spectre.com" in ban_reply_text
    assert "Заблокирован" in ban_reply_text

    # Имитируем сообщение Телеграм от админа для разблокировки
    mock_status_msg_unban = AsyncMock()
    mock_message_unban = AsyncMock()
    mock_message_unban.text = "/unban victim@spectre.com"
    mock_message_unban.reply = AsyncMock(return_value=mock_status_msg_unban)

    await cmd_unban_client(mock_message_unban)

    mock_message_unban.reply.assert_called_once()
    mock_status_msg_unban.edit_text.assert_called_once()
    unban_reply_text = mock_status_msg_unban.edit_text.call_args[0][0]
    assert "victim@spectre.com" in unban_reply_text
    assert "Разблокирован" in unban_reply_text
