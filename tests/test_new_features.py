import pytest
import datetime
from unittest.mock import AsyncMock, patch
from core.spectre_client import SpectrePanelInstance, spectre_manager
from core.spectre_client.log_parser import (
    find_email_and_ip_in_xray_log,
    find_email_in_hysteria_log,
    find_client_ip_for_email_in_hysteria_log
)


def test_log_parser_extended_window_300s():
    """Тест: поиск по логам, созданным до 300 секунд назад (ранее отбрасывались из-за лимита в 12 секунд)."""
    now = datetime.datetime.now()
    log_time_150s_ago = (now - datetime.timedelta(seconds=150)).strftime("%Y/%m/%d %H:%M:%S")

    xray_log = [
        f"{log_time_150s_ago} [info] 192.168.1.50:41234 accepted tcp:13.251.130.193:22 [VLESS-TCP >> direct] email: user_150s@domain.com"
    ]

    res = find_email_and_ip_in_xray_log(xray_log, client_ip=None, dst_ip="13.251.130.193", dst_port=22, max_age_sec=300)
    assert res is not None
    email, ip, tag = res
    assert email == "user_150s@domain.com"
    assert tag == "VLESS-TCP >> direct"


def test_log_parser_singbox_and_bracketed_ip():
    """Тест: разбор логов с квадратными скобками [IP]:Port и IPv6 адресами."""
    now = datetime.datetime.now()
    log_time = now.strftime("%Y/%m/%d %H:%M:%S")

    # Xray log с IP в скобках
    xray_log_bracketed = [
        f"{log_time} [info] 10.0.0.1:55555 accepted tcp:[13.251.130.193]:22 email: bracketed_user@xray.com"
    ]

    res = find_email_and_ip_in_xray_log(xray_log_bracketed, client_ip=None, dst_ip="13.251.130.193", dst_port=22)
    assert res is not None
    email, ip, tag = res
    assert email == "bracketed_user@xray.com"


def test_find_email_in_hysteria_log_json():
    """Тест: разбор JSON логов Hysteria 2 с reqAddr и разными типами полей."""
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    hysteria_json_log = [
        f'{{"time":"{now_utc}","level":"info","msg":"inbound connection","id":"my_double_v2","reqAddr":"13.251.130.193:22"}}'
    ]

    email = find_email_in_hysteria_log(hysteria_json_log, dst_ip="13.251.130.193", dst_port=22)
    assert email == "my_double_v2"


@pytest.mark.asyncio
async def test_manager_docker_exec_fallback(monkeypatch):
    """Тест: проверка fallback чтения логов через docker exec spectre-panel tail."""
    panel = SpectrePanelInstance("LXC Test Panel", "https://192.168.1.65:18894", "token", "ui", "lxc", "104")

    async def mock_subprocess_exec(*args, **kwargs):
        cmd = args
        # Эмулируем ошибку при обычном pct exec tail
        if "tail" in cmd and "docker" not in cmd:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate.return_value = (b"", b"File not found")
            return mock_proc
        # Эмулируем успешный ответ при docker exec spectre-panel tail
        elif "docker" in cmd and "exec" in cmd:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (
                b"2026/08/08 12:30:00 [info] accepted tcp:13.251.130.193:22 email: docker_client@test.com\n",
                b""
            )
            return mock_proc
        
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"Error")
        return mock_proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_subprocess_exec)

    lines = await spectre_manager._read_log_lines(panel, "/app/bin/singbox.log")
    assert len(lines) == 1
    assert "docker_client@test.com" in lines[0]


@pytest.mark.asyncio
async def test_get_client_from_panel_logs_singbox_path(monkeypatch):
    """Тест: поиск клиента Xray/Singbox в /app/bin/singbox.log."""
    panel = SpectrePanelInstance("Singbox Panel", "https://192.168.1.65:18894", "token", "ui", "lxc", "104")

    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    singbox_log_content = [
        f"{now} [info] 10.0.0.1:12345 accepted tcp:13.251.130.193:22 [singbox-inbound] email: singbox_user@domain.com"
    ]

    async def mock_read_log_lines(panel_obj, log_path):
        if "singbox.log" in log_path:
            return singbox_log_content
        return []

    monkeypatch.setattr(spectre_manager, "_read_log_lines", mock_read_log_lines)

    res = await spectre_manager._get_client_from_panel_logs(panel, client_ip=None, dst_ip="13.251.130.193", port=22)
    assert res is not None
    email, source, ip, tag = res
    assert email == "singbox_user@domain.com"
    assert source == "xray"
    assert tag == "singbox-inbound"
