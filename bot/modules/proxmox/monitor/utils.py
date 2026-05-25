import asyncio
import logging
import os
from core.bot import bot
from core.config import settings

class LogTailer:
    """Асинхронный watcher для tail-мониторинга файлов логов или вывода команд (например, journalctl)."""
    def __init__(self, source, callback, *args, **kwargs):
        self.source = source  # Может быть строкой (путь к файлу) или списком аргументов команды (list)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.running = False
        self.task = None

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._run())
        logging.info(f"Запущен tailer для источника: {self.source}")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logging.info(f"Остановлен tailer для источника: {self.source}")

    async def _run(self):
        if isinstance(self.source, list):
            # Если передан список — запускаем как команду (стриминг stdout)
            await self._run_command()
        else:
            # Если передана строка — работаем в режиме чтения файла
            await self._run_file()

    async def _run_command(self):
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.source,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            while self.running:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    if proc.returncode is not None:
                        stderr_bytes = await proc.stderr.read()
                        stderr_text = stderr_bytes.decode('utf-8', errors='ignore').strip()
                        logging.error(f"[LogTailer] Процесс {self.source} завершился с кодом {proc.returncode}. Ошибка: {stderr_text}")
                        break
                    await asyncio.sleep(1)
                    continue
                line = line_bytes.decode('utf-8', errors='ignore')
                await self._trigger_callback(line)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Ошибка в cmd-tailer {self.source}: {e}")
        finally:
            if proc:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=1.5)
                except Exception:
                    try:
                        proc.kill()
                        await asyncio.wait_for(proc.wait(), timeout=1.0)
                    except:
                        pass

    async def _run_file(self):
        try:
            # Если файл еще не создан, ждем его появления
            while self.running and not os.path.exists(self.source):
                await asyncio.sleep(5)
            
            if not self.running:
                return

            with open(self.source, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, os.SEEK_END)
                while self.running:
                    line = f.readline()
                    if not line:
                        await asyncio.sleep(1)
                        continue
                    await self._trigger_callback(line)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Ошибка в file-tailer {self.source}: {e}")

    async def _trigger_callback(self, line):
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(line, *self.args, **self.kwargs)
            else:
                self.callback(line, *self.args, **self.kwargs)
        except Exception as ex:
            logging.error(f"Ошибка при вызове callback в tailer: {ex}")


async def send_alert_to_admins(text, parse_mode="HTML", reply_markup=None):
    """Отправка алертов всем администраторам."""
    if not settings.admin_ids:
        return
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")


def is_private_ip(ip):
    """Проверяет, относится ли IP-адрес к приватным/локальным диапазонам RFC 1918."""
    if not ip or ip == 'UNKNOWN':
        return True
    if ip == '::1' or ip == 'localhost':
        return True
    try:
        parts = list(map(int, ip.split('.')))
        if len(parts) != 4:
            return False
        # 127.0.0.0/8 (Loopback)
        if parts[0] == 127:
            return True
        # 10.0.0.0/8 (Private)
        if parts[0] == 10:
            return True
        # 172.16.0.0/12 (Private)
        if parts[0] == 172 and (16 <= parts[1] <= 31):
            return True
        # 192.168.0.0/16 (Private)
        if parts[0] == 192 and parts[1] == 168:
            return True
        # 169.254.0.0/16 (Link-Local)
        if parts[0] == 169 and parts[1] == 254:
            return True
        return False
    except Exception:
        return False


def detect_xui_service(vmid):
    """Определяет имя системной службы X-UI (x-ui или 3x-ui) внутри контейнера."""
    import subprocess
    import platform
    if platform.system() != 'Linux':
        return "x-ui"
    for svc in ["x-ui", "3x-ui"]:
        try:
            # Выполняем быструю проверку статуса службы в контейнере
            cmd = ["pct", "exec", str(vmid), "--", "systemctl", "is-active", svc]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if res.returncode == 0 or "active" in res.stdout or "inactive" in res.stdout:
                return svc
        except Exception:
            pass
    return "x-ui"

