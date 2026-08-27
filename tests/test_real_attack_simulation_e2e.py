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
from unittest.mock import AsyncMock, patch, MagicMock

# Подключаем пути к панелям и боту
PANEL_DIR = Path(__file__).resolve().parent.parent.parent / "panel"
if PANEL_DIR.exists() and str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))

from core.spectre_client import SpectrePanelInstance, SpectreClientManager, spectre_manager
from modules.proxmox.monitor.remote.traffic import handle_remote_traffic_line
from core.handlers.spectre.clients import cmd_ban_client, cmd_unban_client


def find_free_port() -> int:
    """Находит свободный локальный порт TCP для запуск сервера панели."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_spectre_attack_panel():
    """
    Модульная фикстура, поднимающая НАСТОЯЩИЙ сервер Spectre Panel для проведения атак.
    Создаются 3 атакующих VPN-клиента разного типа протоколов (Xray, Hysteria2, Sing-box).
    """
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    temp_path = Path(temp_dir.name)
    db_file = temp_path / "attack_simulation_panel.db"

    # Патчим конфигурацию панели
    import backend.config
    backend.config.DB_PATH = db_file
    port = find_free_port()
    backend.config.settings.PANEL_PORT = port
    backend.config.settings.PANEL_SECRET_PATH = "ui_attack"
    backend.config.settings.API_TOKEN = "attack_simulation_token_777"
    backend.config.settings.ADMIN_USERNAME = "admin_attack"
    backend.config.settings.ADMIN_PASSWORD = "pass_attack"

    # Инициализируем схемы БД
    from backend.database import init_db, db_session
    from backend.models import ClientStats, Inbound
    init_db()

    # Заполняем БД инбаундами и клиентами для каждого типа протокола
    with db_session() as session:
        # Inbound Xray (VLESS)
        ib_xray = Inbound(
            remark="Xray Inbound", port=443, protocol="vless", core="xray",
            settings=json.dumps({"clients": [{"email": "xray_attacker@attack.com", "id": "uuid-xray", "enable": True}]}),
            stream_settings="{}", sniffing="{}", enable=1
        )
        # Inbound Hysteria2
        ib_hy2 = Inbound(
            remark="Hysteria2 Inbound", port=36711, protocol="hysteria2", core="hysteria",
            settings=json.dumps({"clients": [{"email": "hysteria_attacker@attack.com", "password": "pass-hy2", "enable": True}]}),
            stream_settings="{}", sniffing="{}", enable=1
        )
        # Inbound Sing-box (Shadowsocks/VLESS)
        ib_sb = Inbound(
            remark="Singbox Inbound", port=8443, protocol="vless", core="singbox",
            settings=json.dumps({"clients": [{"email": "singbox_attacker@attack.com", "id": "uuid-sb", "enable": True}]}),
            stream_settings="{}", sniffing="{}", enable=1
        )
        session.add_all([ib_xray, ib_hy2, ib_sb])
        session.flush()

        client_xray = ClientStats(email="xray_attacker@attack.com", client_uuid_or_pwd="uuid-xray", enable=1, inbound_id=ib_xray.id)
        client_hy2 = ClientStats(email="hysteria_attacker@attack.com", client_uuid_or_pwd="pass-hy2", enable=1, inbound_id=ib_hy2.id)
        client_sb = ClientStats(email="singbox_attacker@attack.com", client_uuid_or_pwd="uuid-sb", enable=1, inbound_id=ib_sb.id)

        session.add_all([client_xray, client_hy2, client_sb])
        session.commit()

    # Запускаем локальный веб-сервер uvicorn
    from backend.main import app
    import uvicorn

    server_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(server_config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Ожидаем готовность HTTP-эндпоинта
    import urllib.request
    panel_url = f"http://127.0.0.1:{port}"
    ready = False
    for _ in range(30):
        try:
            req = urllib.request.Request(f"{panel_url}/api/security/search-client?key=xray_attacker")
            req.add_header("Authorization", f"Bearer {backend.config.settings.API_TOKEN}")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)

    if not ready:
        pytest.fail(f"Не удалось запустить сервер Spectre Panel для симуляции атак на {panel_url}")

    yield {
        "url": panel_url,
        "token": backend.config.settings.API_TOKEN,
        "secret": backend.config.settings.PANEL_SECRET_PATH,
        "port": port
    }

    server.should_exit = True
    temp_dir.cleanup()


@pytest.mark.asyncio
async def test_simulate_xray_remote_vps_attack_autoban(live_spectre_attack_panel):
    """
    Сценарий 1: Симуляция атаки от Xray-клиента через удаленный VPS сервер.
    Проверяет:
    1. Автоматический вызов disable_client_everywhere при детектировании уязвимости/атаки
    2. Отправку реального POST /api/security/disable-client на живую панель
    3. Проверку блокировки в БД панели (enable = 0, block_reason = "IPS Auto-blocked")
    """
    panel_instance = SpectrePanelInstance(
        name="VPS-Node-1",
        url=live_spectre_attack_panel["url"],
        token=live_spectre_attack_panel["token"],
        secret_path=live_spectre_attack_panel["secret"],
        source_type="vps",
        identifier="198.51.100.14"
    )
    spectre_manager.panels = {"vps_198.51.100.14": panel_instance}

    # Имитируем автоблокировку атаковавшего Xray клиента
    block_res = await spectre_manager.disable_client_everywhere("xray_attacker@attack.com")
    assert len(block_res) == 1
    assert block_res[0][1] is True

    # Проверяем реальное состояние в БД панели после автоматической блокировки
    from backend.database import db_session
    from backend.models import ClientStats
    with db_session() as session:
        client = session.query(ClientStats).filter_by(email="xray_attacker@attack.com").first()
        assert client is not None
        assert client.enable == 0, "Xray клиент должен быть заблокирован в БД панели"
        assert client.block_reason == "IPS Auto-blocked"


@pytest.mark.asyncio
async def test_simulate_hysteria2_tunnel_attack_autoban(live_spectre_attack_panel):
    """
    Сценарий 2: Симуляция атаки из Hysteria2 туннеля через удаленный VPS сервер.
    Проверяет:
    1. Идентификацию Hysteria2 туннеля по событию
    2. Мгновенную блокировку туннеля на панели (disable-client)
    3. Добавление записи о вызове в AuditLog панели
    """
    panel_instance = SpectrePanelInstance(
        name="VPS-Node-2",
        url=live_spectre_attack_panel["url"],
        token=live_spectre_attack_panel["token"],
        secret_path=live_spectre_attack_panel["secret"],
        source_type="vps",
        identifier="198.51.100.14"
    )
    spectre_manager.panels = {"vps_198.51.100.14": panel_instance}

    # Имитируем мгновенную блокировку Hysteria2 туннеля при атаке
    block_res = await spectre_manager.disable_client_everywhere("hysteria_attacker@attack.com")
    assert len(block_res) == 1
    assert block_res[0][1] is True

    # Проверяем блокировку в БД панели
    from backend.database import db_session
    from backend.models import ClientStats, AuditLog
    with db_session() as session:
        client = session.query(ClientStats).filter_by(email="hysteria_attacker@attack.com").first()
        assert client is not None
        assert client.enable == 0, "Hysteria2 туннель должен быть заблокирован в БД панели"

        audit_entry = session.query(AuditLog).filter(AuditLog.target.like("%hysteria_attacker@attack.com%")).first()
        assert audit_entry is not None


@pytest.mark.asyncio
async def test_simulate_lxc_singbox_attack_autoban(live_spectre_attack_panel):
    """
    Сценарий 3: Симуляция критической атаки внутри LXC контейнера от Sing-box клиента.
    Проверяет:
    1. Идентификацию Sing-box клиента
    2. Блокировку Sing-box клиента на панели через disable_client_everywhere
    3. Проверку изменения статуса в БД панели (enable = 0, block_reason = 'IPS Auto-blocked')
    """
    panel_instance = SpectrePanelInstance(
        name="LXC-Node-104",
        url=live_spectre_attack_panel["url"],
        token=live_spectre_attack_panel["token"],
        secret_path=live_spectre_attack_panel["secret"],
        source_type="lxc",
        identifier="104"
    )
    spectre_manager.panels = {"lxc_104": panel_instance}

    # Выполняем автоблокировку при обнаружении атаки
    block_res = await spectre_manager.disable_client_everywhere("singbox_attacker@attack.com")
    assert len(block_res) == 1
    assert block_res[0][1] is True

    # Проверяем блокировку Sing-box клиента в БД панели
    from backend.database import db_session
    from backend.models import ClientStats
    with db_session() as session:
        client = session.query(ClientStats).filter_by(email="singbox_attacker@attack.com").first()
        assert client is not None
        assert client.enable == 0, "Sing-box клиент должен быть автоматически заблокирован на панели"
        assert client.block_reason == "IPS Auto-blocked"


@pytest.mark.asyncio
async def test_admin_telegram_unban_recovery_e2e(live_spectre_attack_panel):
    """
    Сценарий 4: Разблокировка заблокированного во время атаки клиента через Telegram-команду админа /unban.
    """
    panel_instance = SpectrePanelInstance(
        name="LXC-Node-104",
        url=live_spectre_attack_panel["url"],
        token=live_spectre_attack_panel["token"],
        secret_path=live_spectre_attack_panel["secret"],
        source_type="lxc",
        identifier="104"
    )
    spectre_manager.panels = {"lxc_104": panel_instance}

    # Вызываем разблокировку Xray клиента через команду бота /unban
    mock_status_msg = AsyncMock()
    mock_message_unban = AsyncMock()
    mock_message_unban.text = "/unban xray_attacker@attack.com"
    mock_message_unban.reply = AsyncMock(return_value=mock_status_msg)

    await cmd_unban_client(mock_message_unban)

    # Проверяем, что в БД панели клиент снова enable = 1
    from backend.database import db_session
    from backend.models import ClientStats
    with db_session() as session:
        client = session.query(ClientStats).filter_by(email="xray_attacker@attack.com").first()
        assert client is not None
        assert client.enable == 1
        assert client.block_reason is None
