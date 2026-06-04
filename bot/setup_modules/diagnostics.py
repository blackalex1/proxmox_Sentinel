import shutil
import asyncio

from setup_modules.utils import print_header, print_success, print_warning, print_error, print_info

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
