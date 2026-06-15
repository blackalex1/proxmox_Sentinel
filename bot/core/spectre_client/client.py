import asyncio
import logging
import aiohttp
import json
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def parse_env_content(content: str) -> dict:
    """
    Парсит содержимое .env файла в словарь.
    """
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


async def probe_panel_url(ip: str, port: str) -> str:
    """
    Проверяет доступность панели по HTTPS и HTTP, возвращает рабочий URL.
    """
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for proto in ["https", "http"]:
            url = f"{proto}://{ip}:{port}"
            try:
                async with session.get(url, timeout=2) as response:
                    logging.info("spectre_discovery_panel_responded_via_protocol_status", proto, url, response.status)
                    return url
            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError):
                continue
            except Exception:
                continue
    return f"https://{ip}:{port}"


def normalize_url(url: str) -> Optional[Tuple[str, int]]:
    """
    Извлекает нормализованный хост/IP и порт из URL для надежного сравнения дубликатов.
    """
    try:
        from urllib.parse import urlparse
        if not url.startswith("http://") and not url.startswith("https://"):
            parsed = urlparse("http://" + url)
        else:
            parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        if host:
            return host.lower().strip(), port
    except Exception:
        pass
    return None


class SpectrePanelInstance:
    """
    Представляет инстанс Spectre Panel (локальный LXC или удаленный VPS).
    """
    def __init__(self, name: str, url: str, token: str, secret_path: str, source_type: str, identifier: str, env_path: str = None):
        self.name = name
        self.url = url.rstrip('/')
        self.token = token
        self.secret_path = secret_path.strip('/')
        self.source_type = source_type  # 'lxc' или 'vps'
        self.identifier = identifier    # VMID для LXC, IP для VPS
        self.env_path = env_path
        
    async def request(self, method: str, path: str, **kwargs) -> Tuple[bool, dict]:
        """
        Выполняет авторизованный запрос к API панели.
        """
        url = f"{self.url}/{path.lstrip('/')}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        
        # Для безопасности отключаем жесткую проверку SSL на самоподписанных сертификатах
        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.request(method, url, headers=headers, timeout=5, **kwargs) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return True, data
                        except Exception:
                            # Для бэкапа (может возвращать JSON или файл)
                            text = await response.text()
                            try:
                                return True, json.loads(text)
                            except Exception:
                                return True, {"raw_content": text}
                    else:
                        text = await response.text()
                        logging.warning("spectre_api_error", self.name, response.status, text[:200])
                        return False, {"error": f"HTTP {response.status}", "details": text}
        except Exception as e:
            logging.error("spectre_api_exception_during_request", self.name, e)
            return False, {"error": str(e)}

    async def get_audit_logs(self, limit: int = 10) -> Tuple[bool, dict]:
        """Запрашивает последние записи логов аудита с панели."""
        return await self.request("GET", "/api/security/audit-logs", params={"limit": limit})
