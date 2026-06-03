#!/usr/bin/env python3
import os
import sys
import time
import shutil
import asyncio
import subprocess
import signal
import datetime

# Add parent directory to sys.path to enable importing core and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m' # No Color

def print_header(text):
    print(f"\n{BLUE}=== {text} ==={NC}")

def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠️ {text}{NC}")

def print_error(text):
    print(f"{RED}❌ {text}{NC}")

def print_info(text):
    print(f"{CYAN}i {text}{NC}")

async def check_systemd_service():
    """Check if the proxmox-lxc-bot systemd service is active."""
    print_header("Проверка службы Systemd")
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "is-active", "proxmox-lxc-bot.service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        status = stdout_bytes.decode('utf-8').strip()
        
        if status == "active":
            print_success("Служба proxmox-lxc-bot.service АКТИВНА.")
            return True
        else:
            print_warning(f"Служба proxmox-lxc-bot.service не запущена (Статус: {status}).")
            print_warning("Запустите службу перед началом теста: sudo systemctl start proxmox-lxc-bot.service")
            return False
    except Exception as e:
        print_error(f"Не удалось проверить статус службы через systemctl: {e}")
        return False

async def check_sysctl():
    """Verify net.bridge.bridge-nf-call-iptables sysctl configuration."""
    print_header("Проверка конфигурации моста ядра (Sysctl)")
    try:
        proc = await asyncio.create_subprocess_exec(
            "sysctl", "-n", "net.bridge.bridge-nf-call-iptables",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        val = stdout_bytes.decode('utf-8').strip()
        
        if val == "1":
            print_success("net.bridge.bridge-nf-call-iptables установлен в 1 (трафик моста идет через iptables).")
            return True
        else:
            print_error(f"net.bridge.bridge-nf-call-iptables равен {val} (должен быть 1).")
            print_info("Попробуйте выполнить: sudo sysctl -w net.bridge.bridge-nf-call-iptables=1")
            return False
    except Exception as e:
        print_error(f"Не удалось прочитать параметры sysctl: {e}")
        return False

async def get_running_containers():
    """List running LXC containers on the host."""
    print_header("Поиск запущенных LXC-контейнеров")
    if not shutil.which("pct"):
        print_warning("Утилита pct не найдена. Возможно, этот скрипт запущен не на хосте Proxmox VE.")
        return []
        
    try:
        proc = await asyncio.create_subprocess_exec(
            "pct", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        lines = stdout_bytes.decode('utf-8').splitlines()
        
        running_vmids = []
        # Пропускаем заголовок pct list
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                vmid = parts[0]
                status = parts[1]
                name = parts[2]
                if status == "running":
                    running_vmids.append((int(vmid), name))
                    print_info(f"Обнаружен запущенный контейнер VMID {vmid} ({name})")
                    
        if not running_vmids:
            print_warning("Нет запущенных LXC-контейнеров на этом хосте.")
        return running_vmids
    except Exception as e:
        print_error(f"Ошибка при получении списка контейнеров: {e}")
        return []

async def get_running_vms():
    """List running QEMU VMs to log status details."""
    print_header("Поиск запущенных Виртуальных Машин (QEMU)")
    if not shutil.which("qm"):
        return []
    try:
        proc = await asyncio.create_subprocess_exec(
            "qm", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        lines = stdout_bytes.decode('utf-8').splitlines()
        
        running_vms = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                vmid = parts[0]
                status = parts[2]
                name = parts[1]
                if status == "running":
                    running_vms.append((int(vmid), name))
                    print_info(f"Обнаружена запущенная виртуальная машина QEMU VMID {vmid} ({name})")
        return running_vms
    except Exception as e:
        print_error(f"Ошибка при получении списка виртуальных машин: {e}")
        return []

async def test_host_ips():
    """Test Host IPS connection blocking (VMID 0)."""
    print_header("ТЕСТ 1: Активная защита Хоста Proxmox (vmid=0)")
    
    # Запуск через python (без timeout утилиты) с последующим сном на 5 секунд.
    # Это дает боту достаточно времени (до 4.0 сек) для перехвата лога и убийства процесса,
    # исключая гонку со слишком ранним завершением nc.
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

        # Wait remaining duration to let the bot process the connection event and send SIGKILL
        await asyncio.sleep(3.5)
        
        # Check if the process is still running
        if proc.returncode is None:
            # Process still running, meaning it was not killed
            print_error("ВНИМАНИЕ: Процесс не был убит IPS системой в течение 4 секунд.")
            print_info("Завершаем процесс принудительно для очистки...")
            try:
                proc.terminate()
            except:
                pass
            return False
        else:
            # Process terminated
            duration = time.time() - start_time
            # If terminated by SIGKILL, exit code will be non-zero (often 137 or negative depending on shell/subprocess runner)
            if proc.returncode in [137, -9, -signal.SIGKILL, 124]:  # 124 is timeout's kill status or others
                print_success(f"Процесс был успешно уничтожен IPS (exit code: {proc.returncode}) за {duration:.2f} сек!")
                print_success("Активная защита Хоста (IPS) РАБОТАЕТ корректно.")
                return True
            else:
                print_warning(f"Процесс завершился с кодом {proc.returncode} за {duration:.2f} сек (не по сигналу блокировки).")
                print_info("Возможно, не установлены правила iptables или бот не успел перехватить логи.")
                return False
    except Exception as e:
        print_error(f"Не удалось выполнить тест хоста: {e}")
        return False

async def check_lxc_firewall_enabled(vmid):
    """Check if at least one network interface has firewall=1 enabled in the LXC configuration."""
    conf_path = f"/etc/pve/lxc/{vmid}.conf"
    if not os.path.exists(conf_path):
        return False
    try:
        with open(conf_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("net") and ":" in line:
                    if "firewall=1" in line:
                        return True
    except Exception:
        pass
    return False

async def test_container_ips(vmid, name):
    """Test IPS connection blocking inside a specific LXC container."""
    print_header(f"ТЕСТ: Активная защита LXC {vmid} ({name})")
    
    # Проверка включения Firewall в конфигурации PVE
    if not await check_lxc_firewall_enabled(vmid):
        print_warning(f"В конфигурации LXC {vmid} НЕ обнаружен включенный Сетевой экран (firewall=1)!")
        print_warning(f"Чтобы включить его через CLI: pct set {vmid} -net0 name=eth0,bridge=vmbr0,firewall=1  (замените параметры на ваши)")
        print_warning("Без этого правила фильтрации трафика на мосту PVE не будут работать для этого LXC!")
    
    # Trigger command using pct exec. We check if python3 or python or nc is available in container.
    # We will try python3 first, then python, then nc.
    
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
        
        # Wait for the bot to intercept the connection and kill the process inside the container
        # Increased to 4.5 seconds to account for concurrent locks in PVE (pct exec)
        await asyncio.sleep(4.5)
        
        if proc.returncode is None:
            print_error(f"ВНИМАНИЕ: Процесс в LXC {vmid} не был убит IPS в течение 4.5 секунд.")
            print_info("Завершаем процесс pct exec...")
            try:
                proc.terminate()
            except:
                pass
            return False
        else:
            duration = time.time() - start_time
            # pct exec might return 137 if the inner process was killed by SIGKILL (9) -> 128 + 9 = 137
            # or it might exit with other non-zero status. We also verify it exited quickly.
            if proc.returncode in [137, -9, 255] or duration < 4.0:
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
    
    # Execute the SSH connection command
    # We expect the connection to trigger the local rule, the bot to tail it, and SSH in to kill the pid
    success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
    duration = time.time() - start_time
    
    # If it was killed, the SSH execution will return failure (success=False) and exit quickly
    if not success and duration < 3.5:
        print_success(f"Процесс на VPS {server['ip']} успешно убит удаленным IPS!")
        print_info(f"Длительность: {duration:.2f} сек, Ошибка SSH: {stderr.strip()}")
        print_success(f"Активная защита на VPS {server['ip']} РАБОТАЕТ корректно.")
        return True
    else:
        print_warning(f"Процесс на VPS завершился без принудительной блокировки за {duration:.2f} сек.")
        print_info(f"Результат выполнения: Успешно={success}, Stdout={stdout}, Stderr={stderr}")
        return False

async def verify_journal_logging():
    print_header("Диагностика: Проверка записи логов ядра")
    print_info("Отправка тестового SYN-пакета на 192.0.2.42:22...")
    
    # Try using nc first, fallback to bash tcp
    if shutil.which("nc"):
        trigger_cmd = ["nc", "-w", "1", "192.0.2.42", "22"]
    else:
        trigger_cmd = ["bash", "-c", "echo > /dev/tcp/192.0.2.42/22"]
        
    try:
        proc = await asyncio.create_subprocess_exec(
            *trigger_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.wait(), timeout=2.0)
    except Exception:
        pass
        
    await asyncio.sleep(1.0)
    
    print_info("Поиск записи HOST_CONN_OUT в journalctl...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "journalctl", "-k", "--since", "10 seconds ago", "--no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode('utf-8', errors='ignore')
        
        found = False
        for line in stdout.splitlines():
            if "HOST_CONN_OUT" in line:
                print_success(f"Найдена запись в journalctl: {line.strip()}")
                found = True
                break
                
        if not found:
            print_error("Запись HOST_CONN_OUT НЕ найдена в journalctl за последние 10 секунд!")
            print_info("Проверка dmesg...")
            proc_dmesg = await asyncio.create_subprocess_exec(
                "dmesg",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_dmesg_bytes, _ = await proc_dmesg.communicate()
            stdout_dmesg = stdout_dmesg_bytes.decode('utf-8', errors='ignore')
            dmesg_found = False
            for line in reversed(stdout_dmesg.splitlines()):
                if "HOST_CONN_OUT" in line:
                    print_warning(f"Запись найдена в dmesg, но НЕ в journalctl: {line.strip()}")
                    dmesg_found = True
                    break
            if not dmesg_found:
                print_error("Запись также отсутствует в dmesg. Возможно, правила iptables не работают.")
    except Exception as e:
        print_error(f"Ошибка при диагностике журналов: {e}")

async def test_journal_streaming():
    print_header("Диагностика: Тестирование стриминга journalctl")
    
    for name, cmd in [
        ("С stdbuf", ["stdbuf", "-oL", "journalctl", "-k", "-f", "-n", "0"]),
        ("Без stdbuf", ["journalctl", "-k", "-f", "-n", "0"])
    ]:
        print_info(f"Тестируем стриминг: {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Allow process to start, then trigger connection
            await asyncio.sleep(0.5)
            
            if shutil.which("nc"):
                trigger_cmd = ["nc", "-w", "1", "192.0.2.42", "22"]
            else:
                trigger_cmd = ["bash", "-c", "echo > /dev/tcp/192.0.2.42/22"]
                
            trigger = await asyncio.create_subprocess_exec(
                *trigger_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=3.0)
                line = line_bytes.decode('utf-8', errors='ignore')
                if "HOST_CONN_OUT" in line:
                    print_success(f"[{name}] Успешно получена целевая строка: {line.strip()}")
                else:
                    print_warning(f"[{name}] Получена нецелевая строка: {line.strip()}")
            except asyncio.TimeoutError:
                print_error(f"[{name}] Таймаут: не получено никаких данных за 3 секунды.")
            finally:
                try:
                    proc.terminate()
                    await proc.wait()
                except:
                    pass
                try:
                    trigger.terminate()
                    await trigger.wait()
                except:
                    pass
        except Exception as e:
            print_error(f"Ошибка при запуске {name}: {e}")

def modify_env_value(env_path, key, value, remove=False):
    if not os.path.exists(env_path):
        print_error(f"Файл конфигурации не найден по пути: {env_path}")
        return False

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        found = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(key) and '=' in stripped:
                k, val = stripped.split('=', 1)
                if k.strip() == key:
                    found = True
                    if remove:
                        if ',' in val or key == "TRUSTED_ADMIN_IPS":
                            items = [x.strip() for x in val.split(',') if x.strip()]
                            if value in items:
                                items.remove(value)
                            if items:
                                new_lines.append(f"{key}={','.join(items)}\n")
                                print_info(f"Удаляем {value} из {key} в .env")
                            else:
                                new_lines.append(f"{key}=\n")
                                print_info(f"Очищаем {key} в .env")
                        else:
                            new_lines.append(f"{key}=\n")
                            print_info(f"Очищаем {key} в .env")
                    else:
                        if ',' in val or key == "TRUSTED_ADMIN_IPS":
                            items = [x.strip() for x in val.split(',') if x.strip()]
                            if value not in items:
                                items.append(value)
                            new_lines.append(f"{key}={','.join(items)}\n")
                            print_info(f"Добавляем {value} в {key} в .env")
                        else:
                            new_lines.append(f"{key}={value}\n")
                            print_info(f"Устанавливаем {key}={value} в .env")
                    continue
            new_lines.append(line)

        if not found and not remove:
            print_info(f"Добавляем {key}={value} в конец .env")
            new_lines.append(f"\n{key}={value}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        print_error(f"Ошибка при изменении .env ({key}): {e}")
        return False

async def restart_bot_service():
    print_info("Перезапуск службы proxmox-lxc-bot.service для применения изменений...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", "proxmox-lxc-bot.service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        # Дополнительная пауза на запуск и инициализацию
        await asyncio.sleep(3)
        print_success("Служба бота перезапущена.")
        return True
    except Exception as e:
        print_error(f"Не удалось перезапустить службу бота: {e}")
        return False

async def main():
    test_start_time = datetime.datetime.now()
    if os.name != 'nt' and os.geteuid() != 0:
        print_error("Этот скрипт должен быть запущен с правами ROOT (sudo), чтобы управлять pct и проверять сокеты!")
        sys.exit(1)
        
    print_header("PVE Aegis IPS - Локальная диагностика и активный тест")
    print_info("Инициализация настроек бота...")
    
    try:
        from core.config import settings
        from modules.mihomo.router import unban_router_ip
    except Exception as e:
        print_error(f"Не удалось загрузить core.config или модули роутера: {e}")
        sys.exit(1)

    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    
    # Извлекаем IP хоста Proxmox
    host_ip = None
    if settings.proxmox_host:
        host_ip = settings.proxmox_host.split(':')[0]
    
    if not host_ip:
        try:
            import socket
            host_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            host_ip = "127.0.0.1"

    print_info(f"Определен IP-адрес хоста Proxmox: {host_ip}")
    print_info(f"Активный IPS_PROCESS_WHITELIST из конфигурации: {settings.ips_process_whitelist}")
    

    
    # 1. Вносим хост и временное имя скрипта в белый список, затем перезапускаем бота
    host_whitelist_modified = False
    cmdline_whitelist_modified = False
    
    if host_ip:
        host_whitelist_modified = modify_env_value(env_path, "TRUSTED_ADMIN_IPS", host_ip, remove=False)
        cmdline_whitelist_modified = modify_env_value(env_path, "IPS_TEMP_WHITELIST_CMDLINE", "test_ips.py", remove=False)
        
        if host_whitelist_modified or cmdline_whitelist_modified:
            await restart_bot_service()
            
            # 2. Пытаемся разбанить хост на роутере перед тестами
            print_info(f"Снимаем возможные блокировки для {host_ip} на роутере...")
            try:
                success, desc = await unban_router_ip(host_ip)
                if success:
                    print_success(f"Запрос на разбан отправлен: {desc}")
                else:
                    print_warning(f"Не удалось разбанить на роутере: {desc}")
            except Exception as ex:
                print_error(f"Ошибка при попытке разбанить хост на роутере: {ex}")

    try:
        # Запуск диагностики логов ядра
        await verify_journal_logging()
        await test_journal_streaming()
            
        # Check environments
        service_active = await check_systemd_service()
        sysctl_ok = await check_sysctl()
        
        if not service_active:
            print_warning("Служба бота неактивна. Запустите бота, чтобы он перехватывал логи!")
            
        results = {}
        
        # 1. Test Host
        host_ok = await test_host_ips()
        results["Хост Proxmox VE (vmid=0)"] = host_ok
        
        # 2. Test LXC Containers
        running_lxcs = await get_running_containers()
        for vmid, name in running_lxcs:
            # Check if LXC is in IPS whitelist
            if vmid in settings.ips_lxc_whitelist:
                print_info(f"LXC {vmid} находится в белом списке (IPS Whitelist). Пропускаем тест.")
                results[f"LXC {vmid} ({name})"] = "WHITELISTED"
                continue
                
            lxc_ok = await test_container_ips(vmid, name)
            results[f"LXC {vmid} ({name})"] = lxc_ok
            
        # 3. List VMs (Informational)
        running_vms = await get_running_vms()
        if running_vms:
            print_header("Ограничения архитектуры (Виртуальные машины)")
            print_warning("Обнаружены запущенные QEMU VMs. Они НЕ защищаются PVE Aegis.")
            print_info("Виртуальные машины (QEMU/KVM) полностью изолированы на уровне оборудования.")
            print_info("Бот контролирует только процессы контейнеров LXC и самого Хоста.")
            
        # 4. Test Remote Servers
        if settings.remote_servers:
            print_header("Тестирование удаленных VPS серверов")
            for server in settings.remote_servers:
                vps_ok = await test_remote_vps(server)
                results[f"VPS {server['ip']}"] = vps_ok
                
        # Print Summary Table
        print_header("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        all_ok = True
        for target, status in results.items():
            if status == "WHITELISTED":
                status_str = f"{YELLOW}ПРОПУЩЕНО (РАЗРЕШЕНО / БЕЛЫЙ СПИСОК){NC}"
            else:
                status_str = f"{GREEN}РАБОТАЕТ (ЗАБЛОКИРОВАНО){NC}" if status else f"{RED}НЕ СРАБОТАЛО (НЕТ БЛОКИРОВКИ){NC}"
            print(f" - {target:<35} : {status_str}")
            if status is False:
                all_ok = False
                
        print("\n" + "="*60)
        if all_ok:
            print(f"{GREEN}✓ Все тесты активной защиты (IPS) успешно пройдены!{NC}")
            print("Проверьте ваш Telegram-клиент: там должны появиться алерты блокировки.")
        else:
            print(f"{RED}❌ Некоторые тесты не прошли.{NC}")
            print("Возможные причины:")
            print(" 1. Бот не запущен (sudo systemctl start proxmox-lxc-bot.service).")
            print(" 2. Не настроен Сетевой экран (Firewall) в веб-интерфейсе Proxmox для тестируемых LXC.")
            print(" 3. Вы тестируете контейнер, который находится в IPS_LXC_WHITELIST в config/.env.")
            print(" 4. В системе не установлены правила iptables (проверьте логи: journalctl -u proxmox-lxc-bot).")
            
            print_header("Диагностический дамп логов службы бота (journalctl)")
            try:
                since_time_str = test_start_time.strftime("%Y-%m-%d %H:%M:%S")
                proc = await asyncio.create_subprocess_exec(
                    "journalctl", "-u", "proxmox-lxc-bot.service", "--since", since_time_str, "--no-pager",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout_bytes, _ = await proc.communicate()
                logs = stdout_bytes.decode('utf-8', errors='ignore')
                
                keywords = ["Traffic Monitor", "is_local_bot_process", "Local IPS", "ss -atnup", "proc_name", "whitelist", "recent_bot_ports"]
                for line in logs.splitlines():
                    if any(kw in line for kw in keywords) or "WARNING" in line or "ERROR" in line:
                        print(line)
            except Exception as e:
                print_error(f"Не удалось получить логи из journalctl: {e}")
        print("="*60 + "\n")

    finally:
        # Восстанавливаем исходный белый список
        need_restart = False
        if host_whitelist_modified and host_ip:
            print_header("Очистка настроек после теста (TRUSTED_ADMIN_IPS)")
            modify_env_value(env_path, "TRUSTED_ADMIN_IPS", host_ip, remove=True)
            need_restart = True
            
        if cmdline_whitelist_modified:
            print_header("Очистка настроек после теста (IPS_TEMP_WHITELIST_CMDLINE)")
            modify_env_value(env_path, "IPS_TEMP_WHITELIST_CMDLINE", "test_ips.py", remove=True)
            need_restart = True
            
        if need_restart:
            await restart_bot_service()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nТест прерван пользователем.")
