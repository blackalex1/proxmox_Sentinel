import asyncio
import logging
import os
from core.bot import bot
from core.config import settings

class LogTailer:
    """Асинхронный watcher для tail-мониторинга файлов логов или вывода команд (например, journalctl)."""
    def __init__(self, source, callback, *args, concurrent: bool = True, **kwargs):
        self.source = source  # Может быть строкой (путь к файлу) или списком аргументов команды (list)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.concurrent = concurrent
        self.running = False
        self.task = None
        self._background_tasks = set()

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._run())
        logging.info("tailer_started_for_source", self.source)

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        for t in list(self._background_tasks):
            t.cancel()
        if self._background_tasks:
            try:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            except Exception:
                pass
        logging.info("tailer_stopped_for_source", self.source)

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
                    # EOF reached - subprocess closed stdout and terminated
                    await proc.wait()
                    if self.running and proc.returncode != 0:
                        stderr_bytes = await proc.stderr.read() if proc.stderr else b""
                        stderr_text = stderr_bytes.decode('utf-8', errors='ignore').strip()
                        logging.warning("logtailer_process_terminated_code_error", self.source, proc.returncode, stderr_text)
                    break
                line = line_bytes.decode('utf-8', errors='ignore')
                await self._trigger_callback(line)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error("error_in_cmd-tailer", self.source, e)
        finally:
            if proc:
                try:
                    if proc.returncode is None:
                        proc.kill()
                    await proc.wait()
                except Exception:
                    pass

    async def _run_file(self):
        try:
            while self.running:
                # Если файл еще не создан, ждем его появления
                while self.running and not os.path.exists(self.source):
                    await asyncio.sleep(5)
                
                if not self.running:
                    return

                try:
                    with open(self.source, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, os.SEEK_END)
                        current_ino = os.stat(self.source).st_ino if os.path.exists(self.source) else None
                        while self.running:
                            line = f.readline()
                            if not line:
                                await asyncio.sleep(1)
                                if os.path.exists(self.source):
                                    try:
                                        st = os.stat(self.source)
                                        if (current_ino and st.st_ino != current_ino) or (st.st_size < f.tell()):
                                            logging.info("logtailer_log_rotation_detected", self.source)
                                            break
                                    except Exception:
                                        pass
                                continue
                            await self._trigger_callback(line)
                except (IOError, OSError) as open_err:
                    logging.warning("logtailer_file_read_warning", self.source, open_err)
                    await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error("error_in_file-tailer", self.source, e)

    async def _trigger_callback(self, line):
        try:
            import inspect
            if inspect.iscoroutinefunction(self.callback):
                if self.concurrent:
                    task = asyncio.create_task(self._safe_invoke_callback(line))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                else:
                    await self.callback(line, *self.args, **self.kwargs)
            else:
                self.callback(line, *self.args, **self.kwargs)
        except Exception as ex:
            logging.error("error_executing_callback_in_tailer", ex)

    async def _safe_invoke_callback(self, line):
        try:
            await self.callback(line, *self.args, **self.kwargs)
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            logging.error("error_executing_callback_in_tailer", ex)


def make_progress_bar(pct, length=10):
    """Генерирует текстовую шкалу прогресса из символов ■ и □."""
    pct = max(0.0, min(100.0, pct))
    filled_length = int(round(length * pct / 100))
    return "■" * filled_length + "□" * (length - filled_length)


def convert_rich_html_to_standard(html):
    import re
    if not html:
        return ""
        
    # 1. Mask code blocks (<pre><code>, <code>, ```...```, `...`)
    code_blocks = []
    def mask_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_MASK_{len(code_blocks)-1}__"
        
    html = re.sub(r'<pre\b[^>]*>.*?</pre>', mask_code, html, flags=re.DOTALL)
    html = re.sub(r'<code\b[^>]*>.*?</code>', mask_code, html, flags=re.DOTALL)
    html = re.sub(r'```[\s\S]*?```', mask_code, html)
    html = re.sub(r'`[^`\n]+`', mask_code, html)
        
    # 2. Convert markdown headers: # Header -> <b>Header</b>
    html = re.sub(r'^#+\s+(.*?)$', r'<b>\1</b>\n', html, flags=re.MULTILINE)
    
    # 3. Convert HTML header tags to bold
    html = re.sub(r'</?h[1-6][^>]*>', lambda m: '<b>' if m.group(0).startswith('<h') else '</b>\n', html)
    
    # 4. Convert <hr> / <hr/> / --- to separator
    html = re.sub(r'<hr\s*/?>', '\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n', html)
    html = re.sub(r'^---\s*$', '⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯', html, flags=re.MULTILINE)
    
    # 5. Convert <details><summary>...</summary>...</details> to collapsible expandable blockquote
    def process_details(match):
        summary = match.group(1).strip()
        body = match.group(2).strip()
        summary_clean = re.sub(r'</?(?:b|strong)[^>]*>', '', summary)
        return f"\n<blockquote expandable><b>{summary_clean}</b>\n{body}</blockquote>\n"

    html = re.sub(r'<details\b[^>]*>\s*<summary\b[^>]*>(.*?)</summary>(.*?)</details>', process_details, html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'\s*</?details[^>]*>\s*', '\n', html)
    html = re.sub(r'[ \t]*<summary[^>]*>', '<b>', html)
    html = re.sub(r'</summary>\s*', '</b>\n', html)

    # 6. Convert <tg-thinking>...</tg-thinking> to placeholder
    html = re.sub(r'<tg-thinking\b[^>]*>(.*?)</tg-thinking>', r'⏳ <i>\1</i>', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 7. Convert <aside> to blockquote
    html = re.sub(r'<aside[^>]*>', '<blockquote>', html)
    html = re.sub(r'</aside>', '</blockquote>', html)
    
    # 8. Convert footer/cite
    html = re.sub(r'<footer[^>]*>', '<i>', html)
    html = re.sub(r'</footer>', '</i>', html)
    html = re.sub(r'<cite[^>]*>', '\n— ', html)
    html = re.sub(r'</cite>', '', html)
    
    # 9. Convert <br/> to newline
    html = re.sub(r'<br\s*/?>', '\n', html)
    
    # 10. For HTML tables, extract rows and clean up
    def process_table(table_match):
        table_content = table_match.group(1)
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', table_content, flags=re.DOTALL)
        result_rows = []
        for row in rows:
            headers = re.findall(r'<th\b[^>]*>(.*?)</th>', row, flags=re.DOTALL)
            if headers:
                continue
            cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, flags=re.DOTALL)
            if len(cells) == 2:
                result_rows.append(f"{cells[0].strip()}: {cells[1].strip()}")
            elif cells:
                result_rows.append(" - ".join([c.strip() for c in cells]))
        return "\n" + "\n".join(result_rows) + "\n"

    html = re.sub(r'<table[^>]*>(.*?)</table>', process_table, html, flags=re.DOTALL)

    # 11. For markdown tables: | Param | Value | -> Param: Value
    lines = html.split('\n')
    out_lines = []
    for line in lines:
        trimmed = line.strip()
        if trimmed.startswith('|') and trimmed.endswith('|'):
            parts = [p.strip() for p in trimmed.strip('|').split('|')]
            if any(p.startswith(':--') or p.startswith('---') for p in parts):
                continue
            if len(parts) == 2:
                if parts[0] in ("Параметр", "Parameter", "Metric", "Показатель"):
                    continue
                out_lines.append(f"{parts[0]}: {parts[1]}")
            else:
                out_lines.append(" - ".join(parts))
        else:
            out_lines.append(line)
    html = '\n'.join(out_lines)
    
    # 12. Convert markdown bold **...** -> <b>...</b> and italic *...* -> <i>...</i>
    html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
    html = re.sub(r'(?<!\*)\*([^\*\n]+)\*(?!\*)', r'<i>\1</i>', html)
    
    # 13. Restore code blocks
    for idx, block in enumerate(code_blocks):
        if block.startswith('```') and block.endswith('```'):
            inner = block.strip('`').strip('\n')
            block = f"<pre><code>{inner}</code></pre>"
        elif block.startswith('`') and block.endswith('`'):
            inner = block.strip('`')
            block = f"<code>{inner}</code>"
        html = html.replace(f"__CODE_BLOCK_MASK_{idx}__", block)
    
    # 14. Strip any other unrecognized/unsupported HTML tags that might fail Telegram's parse_mode="HTML"
    def strip_unsupported_tags(match):
        full_tag = match.group(0)
        tag = match.group(1).lower()
        is_closing = tag.startswith('/')
        tag_name = tag[1:] if is_closing else tag
        if tag_name in ('a', 'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'span', 'code', 'pre', 'blockquote', 'tg-spoiler', 'tg-emoji'):
            return full_tag
        return ''
        
    html = re.sub(r'<(/?[a-zA-Z0-9_-]+)(?:\s+[^>]*)?>', strip_unsupported_tags, html)
    
    # Clean double spaces and double newlines
    html = re.sub(r'[ \t]+', ' ', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()


from core.sender import (
    send_rich_message,
    edit_rich_message,
    send_rich_message_draft,
    send_alert_to_admins,
)




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


async def get_geoip_info(ip: str) -> str:
    """Получает геологикационную информацию (страна, город, провайдер) для IP-адреса."""
    if not ip or ip == "unknown" or ip == "WEB_GUI" or ip == "LOCAL":
        return "Локальная сеть"
    
    # Игнорируем RFC 1918 приватные адреса и IPv6 loopback
    if ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16.") or ip.startswith("::1") or ip == "localhost":
        return "Локальная сеть"
        
    try:
        import aiohttp
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org"
        session = await bot.session.create_session()
        async with session.get(url, timeout=3.0) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "success":
                    country = data.get("country", "")
                    city = data.get("city", "")
                    isp = data.get("isp") or data.get("org") or ""
                    geo_parts = []
                    if country:
                        geo_parts.append(country)
                    if city:
                        geo_parts.append(city)
                    geo_str = " - ".join(geo_parts) if geo_parts else ""
                    if isp:
                        if geo_str:
                            return f"{geo_str} ({isp})"
                        return isp
                    return geo_str or "Определено"
    except Exception as e:
        logging.warning("geoip_failed_to_obtain_data_for", ip, e)
    return "Неизвестно"




