import sys
import time
import asyncio
import signal
import shutil

from setup_modules.utils import print_header, print_success, print_warning, print_error, print_info
from setup_modules.checks import check_lxc_firewall_enabled

async def test_host_ips():
    """Test Host IPS connection blocking (VMID 0)."""
    print_header("ТЕСТ 1: Активная защита Хоста Proxmox (vmid=0)")
    
    # Try using trigger connect process to test IPS
    test_cmd = [
        sys.executable, "-c",
        "import socket, time; s=socket.socket(); s.settimeout(2); s.connect_ex(('192.0.2.42', 22)); time.sleep(5)"
    ]
    
    print_info(f"Запуск дочернего процесса: {' '.join(test_cmd)}")
    start_time = time.time()
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait a short duration to let the connection establish and check it via ss
        await asyncio.sleep(0.5)
        print_info("Диагностика сокетов: Проверка активных соединений (ss)...")
        try:
            ss_proc = await asyncio.create_subprocess_exec(
                "ss", "-atnup",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            ss_out, ss_err = await ss_proc.communicate()
            ss_lines = ss_out.decode('utf-8', errors='ignore').splitlines()
            found_socket = False
            for line in ss_lines:
                if "192.0.2.42" in line:
                    print_success(f"Найдено активное соединение в ss: {line.strip()}")
                    found_socket = True
            if not found_socket:
                print_warning("В выводе ss не обнаружено соединений с 192.0.2.42. Возможно, оно уже закрыто или не было установлено.")
        except Exception as ss_ex:
            print_error(f"Не удалось выполнить команду ss: {ss_ex}")

        # Poll the process return code for up to 6 seconds
        max_wait = 6.0
        poll_interval = 0.1
        start_wait = time.time()
        while time.time() - start_wait < max_wait:
            if proc.returncode is not None:
                break
            await asyncio.sleep(poll_interval)
        
        # Check if the process is still running
        if proc.returncode is None:
            print_error("ВНИМАНИЕ: Процесс не был убит IPS системой.")
            print_info("Завершаем процесс принудительно для очистки...")
            try:
                proc.terminate()
            except:
                pass
            return False
        else:
            duration = time.time() - start_time
            sig_kill = getattr(signal, 'SIGKILL', 9)
            if proc.returncode in [137, -9, -sig_kill, 124]:
                print_success(f"Процесс был успешно уничтожен IPS (exit code: {proc.returncode}) за {duration:.2f} сек!")
                print_success("Активная защита Хоста (IPS) РАБОТАЕТ корректно.")
                return True
            else:
                print_warning(f"Процесс заверсился с кодом {proc.returncode} за {duration:.2f} сек (не по сигналу блокировки).")
                print_info("Возможно, не установлены правила iptables или бот не успел перехватить логи.")
                return False
    except Exception as e:
        print_error(f"Не удалось выполнить тест хоста: {e}")
        return False

async def benchmark_ips_latency():
    """Benchmark the latency of the IPS engine blocking connection."""
    print_header("БЕНЧМАРК: Измерение быстродействия IPS (время реакции)")
    
    test_cmd = [
        sys.executable, "-c",
        "import socket, time; s=socket.socket(); s.settimeout(2); s.connect_ex(('192.0.2.42', 22)); time.sleep(5)"
    ]
    
    print_info("Запуск триггера подключения для замера задержки...")
    start_time = time.perf_counter()
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Опрашиваем с интервалом в 1 мс
        timeout = 5.0
        poll_interval = 0.001
        killed = False
        
        while time.perf_counter() - start_time < timeout:
            if proc.returncode is not None:
                killed = True
                break
            await asyncio.sleep(poll_interval)
            
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        if killed:
            sig_kill = getattr(signal, 'SIGKILL', 9)
            if proc.returncode in [137, -9, -sig_kill, 124]:
                print_success(f"Процесс был принудительно завершен IPS за {duration_ms:.2f} мс (код выхода: {proc.returncode})!")
                return duration_ms
            else:
                print_warning(f"Процесс завершился с кодом {proc.returncode} за {duration_ms:.2f} мс (не похоже на блокировку IPS).")
                return None
        else:
            print_error(f"Превышено время ожидания ({timeout} сек). Процесс не был убит.")
            try:
                proc.terminate()
            except:
                pass
            return None
    except Exception as e:
        print_error(f"Ошибка при проведении бенчмарка: {e}")
        return None

async def test_container_ips(vmid, name):
    """Test IPS connection blocking inside a specific LXC container."""
    print_header(f"ТЕСТ: Активная защита LXC {vmid} ({name})")
    
    if not await check_lxc_firewall_enabled(vmid):
        print_warning(f"В конфигурации LXC {vmid} НЕ обнаружен включенный Сетевой экран (firewall=1)!")
        print_warning(f"Чтобы включить его через CLI: pct set {vmid} -net0 name=eth0,bridge=vmbr0,firewall=1  (замените параметры на ваши)")
        print_warning("Без этого правила фильтрации трафика на мосту PVE не будут работать для этого LXC!")
    
    # Detect available command inside container
    detect_cmds = [
        ["pct", "exec", str(vmid), "--", "which", "python3"],
        ["pct", "exec", str(vmid), "--", "which", "python"],
        ["pct", "exec", str(vmid), "--", "which", "nc"]
    ]
    
    trigger_cmd = None
    for detect in detect_cmds:
        try:
            proc = await asyncio.create_subprocess_exec(
                *detect,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                cmd_path = stdout.decode('utf-8').strip()
                if "python3" in detect[-1]:
                    trigger_cmd = ["pct", "exec", str(vmid), "--", cmd_path, "-c", "import socket, time; s=socket.socket(); s.settimeout(2); s.connect_ex(('192.0.2.42', 22)); time.sleep(5)"]
                elif "python" in detect[-1]:
                    trigger_cmd = ["pct", "exec", str(vmid), "--", cmd_path, "-c", "import socket, time; s=socket.socket(); s.connect_ex(('192.0.2.42', 22)); time.sleep(5)"]
                else:
                    trigger_cmd = ["pct", "exec", str(vmid), "--", "timeout", "5", cmd_path, "-w", "2", "192.0.2.42", "22"]
                break
        except Exception:
            continue
            
    if not trigger_cmd:
        print_warning(f"Внутри контейнера {vmid} не найдены python3, python или nc. Попытка использовать bash fallback...")
        trigger_cmd = ["pct", "exec", str(vmid), "--", "timeout", "5", "bash", "-c", "echo > /dev/tcp/192.0.2.42/22 && sleep 5"]

    print_info(f"Запуск в контейнере: {' '.join(trigger_cmd)}")
    start_time = time.time()
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *trigger_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Poll the process return code for up to 8 seconds
        max_wait = 8.0
        poll_interval = 0.1
        start_wait = time.time()
        while time.time() - start_wait < max_wait:
            if proc.returncode is not None:
                break
            await asyncio.sleep(poll_interval)
        
        if proc.returncode is None:
            print_error(f"ВНИМАНИЕ: Процесс в LXC {vmid} не был убит IPS в течение {max_wait} секунд.")
            print_info("Завершаем процесс pct exec...")
            try:
                proc.terminate()
            except:
                pass
            return False
        else:
            duration = time.time() - start_time
            if proc.returncode in [137, -9, 255] or duration < 7.0:
                print_success(f"Процесс внутри LXC {vmid} успешно убит IPS (Код выхода: {proc.returncode}, Длительность: {duration:.2f} сек)!")
                print_success(f"Активная защита LXC {vmid} РАБОТАЕТ корректно.")
                return True
            else:
                print_warning(f"Процесс внутри LXC завершился с кодом {proc.returncode} за {duration:.2f} сек (не похоже на принудительную блокировку).")
                return False
    except Exception as e:
        print_error(f"Ошибка при выполнении теста в LXC {vmid}: {e}")
        return False

async def test_remote_vps(server):
    """Test remote VPS IPS connection blocking."""
    print_header(f"ТЕСТ: Активная защита удаленного VPS ({server['ip']})")
    
    try:
        from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
    except ImportError:
        print_error("Не удалось импортировать модули SSH. Убедитесь, что зависимости (asyncssh) установлены.")
        return False

    # Check remote commands (python3, python, or nc)
    print_info("Определение доступных утилит на VPS...")
    has_python3, _, _ = await run_remote_ssh_cmd(server, ["which python3"])
    has_python, _, _ = await run_remote_ssh_cmd(server, ["which python"])
    has_nc, _, _ = await run_remote_ssh_cmd(server, ["which nc"])
    
    if has_python3:
        cmd = ["python3 -c \"import socket, time; s=socket.socket(); s.settimeout(2); s.connect_ex(('192.0.2.42', 22)); time.sleep(5)\""]
    elif has_python:
        cmd = ["python -c \"import socket, time; s=socket.socket(); s.connect_ex(('192.0.2.42', 22)); time.sleep(5)\""]
    elif has_nc:
        cmd = ["timeout 5 nc -w 2 192.0.2.42 22"]
    else:
        cmd = ["timeout 5 bash -c \"echo > /dev/tcp/192.0.2.42/22 && sleep 5\""]
        
    print_info(f"Запуск триггера подключения на VPS: {cmd[0]}")
    start_time = time.time()
    
    success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
    duration = time.time() - start_time
    
    if not success and duration < 3.5:
        print_success(f"Процесс на VPS {server['ip']} успешно убит удаленным IPS!")
        print_info(f"Длительность: {duration:.2f} сек, Ошибка SSH: {stderr.strip()}")
        print_success(f"Активная защита на VPS {server['ip']} РАБОТАЕТ корректно.")
        return True
    else:
        print_warning(f"Процесс на VPS завершился без принудительной блокировки за {duration:.2f} сек.")
        print_info(f"Результат выполнения: Успешно={success}, Stdout={stdout}, Stderr={stderr}")
        return False


async def test_router_monitoring(settings):
    """Test router connection and logging correctness."""
    print_header("ТЕСТ 5: Проверка подключения к роутеру через SSH")
    
    ssh_ok = True
    
    # Проверяем SSH соединение к роутеру и утилиты логирования
    if settings.router_monitor_enable:
        print_info(f"Проверка SSH-подключения к роутеру: {settings.router_ssh_user}@{settings.router_ssh_host}:{settings.router_ssh_port}")
        
        from modules.router.router import run_router_ssh_cmd
        ok, stdout, stderr = await run_router_ssh_cmd("echo 'Aegis Test'")
        if ok:
            print_success(f"SSH-подключение к роутеру успешно! Ответ: '{stdout}'")
            
            # Проверяем утилиты логирования в зависимости от режима
            mode = getattr(settings, 'router_monitor_mode', 'conntrack').lower()
            print_info(f"Активный режим мониторинга роутера: {mode}")
            
            path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
            
            if mode == 'conntrack':
                print_info("Проверяем наличие утилиты conntrack на роутере...")
                ok_ct, stdout_ct, stderr_ct = await run_router_ssh_cmd(f"{path_prefix}which conntrack")
                if ok_ct:
                    print_success(f"Утилита conntrack найдена: {stdout_ct.strip()}")
                    # Проверяем может ли conntrack выводить логи
                    ok_run, _, stderr_run = await run_router_ssh_cmd(f"{path_prefix}conntrack -L -p tcp -g -h 2>/dev/null || conntrack -h")
                    if ok_run:
                        print_success("Модуль ядра conntrack активен и готов к стримингу.")
                    else:
                        print_warning(f"Утилита conntrack присутствует, но возникла ошибка при тестовом запуске: {stderr_run}")
                else:
                    print_error("Утилита conntrack НЕ НАЙДЕНА на роутере! Режим conntrack работать не будет.")
                    ssh_ok = False
                    
            elif mode in ('iptables', 'syslog'):
                from modules.router.monitor.rules import setup_router_logging_rules, remove_router_logging_rules
                print_info("Пробуем применить временные правила логирования портов на роутере...")
                rules_ok = await setup_router_logging_rules()
                if rules_ok:
                    print_success("Правила логирования (iptables/nftables) успешно применены на роутере.")
                    await remove_router_logging_rules()
                    print_info("Временные правила логирования успешно удалены.")
                else:
                    print_error("Не удалось применить правила логирования на роутере.")
                    ssh_ok = False
                    
                # Дополнительно проверяем утилиту чтения логов
                if settings.router_type == 'openwrt':
                    ok_lr, stdout_lr, _ = await run_router_ssh_cmd(f"{path_prefix}which logread")
                    if ok_lr:
                        print_success(f"Утилита logread найдена: {stdout_lr.strip()}")
                    else:
                        print_error("Утилита logread не найдена на OpenWrt роутере!")
                        ssh_ok = False
                else:
                    ok_msg, _, stderr_msg = await run_router_ssh_cmd("tail -n 1 /var/log/messages")
                    if ok_msg:
                        print_success("Лог-файл /var/log/messages доступен для чтения.")
                    else:
                        print_error(f"Файл /var/log/messages недоступен: {stderr_msg}")
                        ssh_ok = False
        else:
            print_error(f"Не удалось подключиться по SSH к роутеру: {stderr}")
            ssh_ok = False
    else:
        print_info("Мониторинг роутера через SSH отключен в настройках.")
            
    return ssh_ok
