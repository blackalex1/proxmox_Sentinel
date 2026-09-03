import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from modules.proxmox.monitor.utils import LogTailer
from modules.proxmox.monitor.remote.traffic import handle_remote_traffic_line, recent_remote_traffic_alerts


@pytest.mark.asyncio
async def test_logtailer_concurrent_does_not_block_stream():
    """Проверяет, что LogTailer в concurrent=True режиме не зависает при медленном callback."""
    invocations = []
    
    async def slow_callback(line):
        invocations.append((line, asyncio.get_event_loop().time()))
        await asyncio.sleep(0.5)

    tailer = LogTailer(source="mock_file", callback=slow_callback, concurrent=True)
    
    start_time = asyncio.get_event_loop().time()
    for i in range(5):
        await tailer._trigger_callback(f"line_{i}")
    elapsed = asyncio.get_event_loop().time() - start_time
    
    # 5 вызовов по 0.5s не должны блокировать цикл стрима последовательно
    assert elapsed < 0.1
    assert len(tailer._background_tasks) == 5
    
    await tailer.stop()


@pytest.mark.asyncio
async def test_rapid_burst_iptables_duplicate_throttling(monkeypatch):
    """
    Проверяет, что лавина одинаковых сетевых пакетов iptables отбрасывается мгновенно
    без повторных расследований и спама в Telegram.
    """
    recent_remote_traffic_alerts.clear()

    telegram_alerts = []
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.send_alert_to_admins",
        AsyncMock(side_effect=lambda text, **kw: telegram_alerts.append(text))
    )
    monkeypatch.setattr(
        "modules.proxmox.monitor.remote.traffic.get_and_kill_remote_process",
        AsyncMock(return_value=(None, None))
    )

    iptables_line = "Sep 03 22:09:08 vps kernel: [123.456] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=194.87.29.14 DST=140.82.121.3 LEN=60 PROTO=TCP SPT=48123 DPT=22"
    server_vps = {'ip': '194.87.29.14', 'user': 'root', 'key': 'key_path'}

    # 1. Первый пакет триггерит алерт
    await handle_remote_traffic_line(iptables_line, server=server_vps)
    assert len(telegram_alerts) == 1

    # 2. Пакеты, пришедшие сразу следом (ретрансмиссии с другими SPT), отбрасываются троттлингом
    burst_line_2 = "Sep 03 22:09:09 vps kernel: [123.457] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=194.87.29.14 DST=140.82.121.3 LEN=60 PROTO=TCP SPT=48124 DPT=22"
    burst_line_3 = "Sep 03 22:09:10 vps kernel: [123.458] REMOTE_CONN_OUT: IN= OUT=eth0 SRC=194.87.29.14 DST=140.82.121.3 LEN=60 PROTO=TCP SPT=48125 DPT=22"
    
    await handle_remote_traffic_line(burst_line_2, server=server_vps)
    await handle_remote_traffic_line(burst_line_3, server=server_vps)

    # Количество алертов не изменилось — лавина отброшена
    assert len(telegram_alerts) == 1
