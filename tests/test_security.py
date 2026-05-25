import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from modules.proxmox.monitor.traffic.killer import get_and_kill_local_or_lxc_process
from modules.proxmox.monitor.traffic.firewall import block_local_ip
from modules.proxmox.monitor.remote.hysteria import handle_remote_hysteria_line
from modules.proxmox.monitor.remote.hysteria.alerts import recent_hysteria_violations

@pytest.mark.asyncio
async def test_get_and_kill_local_process():
    # Временно очищаем белый список процессов для теста
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    try:
        # Сценарий 1: Локальный процесс на хосте (vmid == 0)
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'users:(("sshd",pid=12345,fd=3)) :22 ', b"")
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            assert proc_name == "sshd"
            assert pid == "12345"
            
            # Проверяем, что был выполнен ss и соответствующий kill -9
            mock_exec.assert_any_call("ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            mock_exec.assert_any_call("kill", "-9", "12345", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_get_and_kill_lxc_process():
    # Временно очищаем белый список процессов для теста
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    try:
        # Сценарий 2: Процесс внутри LXC контейнера (vmid == 101)
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'users:(("nginx",pid=9876,fd=4)) :80 ', b"")
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=101, spt=80)
            assert proc_name == "nginx"
            assert pid == "9876"
            
            # Проверяем pct exec для получения сокетов и pct exec для kill -9
            mock_exec.assert_any_call("pct", "exec", "101", "--", "ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            mock_exec.assert_any_call("pct", "exec", "101", "--", "kill", "-9", "9876", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_get_and_kill_whitelisted_process():
    # Сценарий 3: Попытка убить защищенный процесс из белого списка
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b'users:(("systemd",pid=1,fd=5)) :22 ', b"")
    
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    # Временно добавляем systemd в белый список
    settings.ips_process_whitelist = ["systemd"]
    
    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            assert proc_name == "systemd"
            assert pid == "WHITELISTED"
            
            # Проверяем, что ss выполнился, а kill -9 НЕ вызывался
            mock_exec.assert_any_call("ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            # Убеждаемся, что kill не вызывался
            for call in mock_exec.call_args_list:
                assert call[0][0] != "kill"
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_block_local_ip():
    mock_proc = AsyncMock()
    mock_proc.wait.return_value = 0
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_proc) as mock_shell:
        success = await block_local_ip("198.51.100.42", delay=1)
        assert success is True
        
        # Проверяем, что были выполнены команды iptables на блокировку
        mock_shell.assert_any_call(
            "iptables -I OUTPUT -d 198.51.100.42 -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        mock_shell.assert_any_call(
            "iptables -I FORWARD -d 198.51.100.42 -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

@pytest.mark.asyncio
async def test_hysteria_warning_accumulation_and_ban():
    # Очищаем историю нарушений для чистоты теста
    recent_hysteria_violations.clear()
    
    server = {
        'ip': '192.168.1.99',
        'user': 'root',
        'key': 'config/dummy_key'
    }
    
    # 1. Формируем тестовые TCP лог-линии на sensitive порты
    tcp_error_line = (
        "May 25 03:00:00 server hysteria-server[100]: "
        "TCP error {\"id\": \"hacker_user\", \"addr\": \"203.0.113.5:54321\", "
        "\"reqAddr\": \"10.0.0.5:22\", \"error\": \"connection timed out\"}"
    )
    
    # Мокаем отправку алертов и функцию бана
    with patch("modules.proxmox.monitor.remote.hysteria.send_alert_to_admins", AsyncMock()) as mock_alert, \
         patch("modules.proxmox.monitor.remote.hysteria.block_remote_hysteria_user", AsyncMock(return_value=True)) as mock_block:
         
        # Попытка 1: Должен добавиться 1 варн
        await handle_remote_hysteria_line(tcp_error_line, server=server)
        assert len(recent_hysteria_violations.get("hacker_user", [])) == 1
        mock_alert.assert_called_once()
        mock_block.assert_not_called()
        
        mock_alert.reset_mock()
        
        # Попытка 2: Должен добавиться 2-й варн (но оповещение задросселировано)
        await handle_remote_hysteria_line(tcp_error_line, server=server)
        assert len(recent_hysteria_violations.get("hacker_user", [])) == 2
        mock_alert.assert_not_called()  # Оповещение задросселировано
        mock_block.assert_not_called()
        
        mock_alert.reset_mock()
        
        # Попытка 3: Должен сработать автоматический бан (3+ попытки)
        await handle_remote_hysteria_line(tcp_error_line, server=server)
        
        # Проверяем, что была вызвана блокировка пользователя
        mock_block.assert_called_once_with(server, "hacker_user")
        # Проверяем, что админы получили уведомление о бане (не дросселируется)
        mock_alert.assert_called_once()
        # Проверяем, что после бана счетчик нарушений сброшен
        assert len(recent_hysteria_violations.get("hacker_user", [])) == 0

@pytest.mark.asyncio
async def test_get_and_kill_self_defense_bot_itself():
    import os
    my_pid = os.getpid()
    
    # Сценарий: Процесс имеет PID самого бота
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (f'users:(("python3",pid={my_pid},fd=3)) :22 '.encode(), b"")
    
    # Временно очищаем белый список процессов
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            
            # Проверяем, что процесс распознан как WHITELISTED (самозащита сработала)
            assert proc_name == "python3"
            assert pid == "WHITELISTED"
            
            # Проверяем, что ss выполнился, а kill -9 НЕ вызывался
            mock_exec.assert_any_call("ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            for call in mock_exec.call_args_list:
                assert call[0][0] != "kill"
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_get_and_kill_self_defense_child_process():
    import os
    my_pid = os.getpid()
    child_pid = 99999
    
    # Сценарий: Процесс имеет другой PID, но его родитель - наш бот
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (f'users:(("python3",pid={child_pid},fd=3)) :22 '.encode(), b"")
    
    # Временно очищаем белый список процессов
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    # Мокаем проверку PPid в файле /proc/99999/status с правильной поддержкой контекстного менеджера с-команды
    mock_open = patch("builtins.open", MagicMock(side_effect=lambda path, *args, **kwargs: 
        MagicMock(__enter__=lambda s: s, __exit__=lambda s, *a: None, __iter__=lambda s: iter([f"Name: python3\n", f"PPid: {my_pid}\n"])) if "99999" in str(path) else open(path, *args, **kwargs)
    ))
    
    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec, \
             patch("os.path.exists", return_value=True), \
             mock_open:
             
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            
            # Проверяем, что процесс распознан как дочерний (WHITELISTED)
            assert proc_name == "python3"
            assert pid == "WHITELISTED"
            
            # Проверяем, что kill -9 НЕ вызывался
            for call in mock_exec.call_args_list:
                assert call[0][0] != "kill"
    finally:
        settings.ips_process_whitelist = original_whitelist


