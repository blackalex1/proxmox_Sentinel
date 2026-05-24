import aiohttp
import logging
import json
import base64
from urllib.parse import urlparse, quote
from core.config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD, XUI_API_TOKEN

class XuiClient:
    def __init__(self):
        self.host = XUI_HOST.rstrip('/') if XUI_HOST else ""
        self.username = XUI_USERNAME
        self.password = XUI_PASSWORD
        self.token = XUI_API_TOKEN
        self.session = None
        self.last_login_attempt = 0
        self.login_cooldown = 10  # секунд ожидания перед повторной попыткой входа после неудачи
        self.csrf_token = ""

    async def get_session(self):
        if self.session is None or self.session.closed:
            # Отключаем проверку SSL сертификата, так как панель доступна по IP (https://192.168.x.x)
            connector = aiohttp.TCPConnector(ssl=False)
            # Разрешаем сохранять куки для IP адресов
            jar = aiohttp.CookieJar(unsafe=True)
            self.session = aiohttp.ClientSession(connector=connector, cookie_jar=jar)
        return self.session

    async def login(self):
        if not self.host or self.token: return False
        
        import time
        now = time.time()
        if now - self.last_login_attempt < self.login_cooldown:
            # Защита от спама авторизации: если предыдущая попытка провалилась недавно
            return False
            
        self.last_login_attempt = now
        try:
            session = await self.get_session()
            
            # Сначала запрашиваем CSRF-токен
            csrf_url = f"{self.host}/csrf-token"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": self.host,
                "Origin": self.host
            }
            try:
                async with session.get(csrf_url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        res_json = await response.json(content_type=None)
                        if isinstance(res_json, dict) and res_json.get("success"):
                            self.csrf_token = res_json.get("obj", "")
            except Exception as e:
                logging.error(f"Failed to fetch XUI CSRF Token: {e}")
                
            if self.csrf_token:
                headers["X-CSRF-Token"] = self.csrf_token
                
            url = f"{self.host}/login"
            payload = {"username": self.username, "password": self.password}
            
            # 1. Пробуем современный способ: отправка как JSON
            try:
                async with session.post(url, json=payload, headers=headers, timeout=5) as response:
                    # Избегаем ContentTypeError с помощью content_type=None
                    result = await response.json(content_type=None)
                    if isinstance(result, dict) and result.get('success'):
                        self.last_login_attempt = 0
                        return True
            except Exception:
                result = None
                
            # 2. Пробуем традиционный способ: Form Data
            try:
                async with session.post(url, data=payload, headers=headers, timeout=5) as response:
                    result = await response.json(content_type=None)
                    if isinstance(result, dict) and result.get('success'):
                        self.last_login_attempt = 0
                        return True
            except Exception:
                result = None
                
            if isinstance(result, dict):
                logging.error(f"XUI Login failed: {result.get('msg')}")
            else:
                status_code = response.status if 'response' in locals() else 'unknown'
                logging.error(f"XUI Login failed: Не удалось войти в панель (код: {status_code})")
            return False
        except Exception as e:
            logging.error(f"XUI Login error: {e}")
            return False

    async def _request(self, method, endpoint, **kwargs):
        if not self.host: return {}
        session = await self.get_session()
        
        # Добавляем Bearer Token или CSRF Token в заголовки
        headers = kwargs.get('headers', {})
        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"
        elif self.csrf_token:
            headers['X-CSRF-Token'] = self.csrf_token
            headers['Referer'] = self.host
            headers['Origin'] = self.host
            headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        kwargs['headers'] = headers
        
        # Если токена нет, то первая попытка и куки/csrf отсутствуют -> логинимся
        if not self.token and (not session.cookie_jar or not self.csrf_token):
            await self.login()
            if self.csrf_token:
                headers = kwargs.get('headers', {})
                headers['X-CSRF-Token'] = self.csrf_token
                headers['Referer'] = self.host
                headers['Origin'] = self.host
                headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                kwargs['headers'] = headers
            
        url = f"{self.host}{endpoint}"
        try:
            async with session.request(method, url, **kwargs) as response:
                # Пытаемся авторизоваться заново при ошибке 401 или 403
                if response.status in (401, 403) and not self.token:
                    if await self.login():
                        if self.csrf_token:
                            headers = kwargs.get('headers', {})
                            headers['X-CSRF-Token'] = self.csrf_token
                            headers['Referer'] = self.host
                            headers['Origin'] = self.host
                            headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                            kwargs['headers'] = headers
                        async with session.request(method, url, **kwargs) as retry_response:
                            try:
                                return await retry_response.json(content_type=None)
                            except:
                                return {}
                    return {}
                
                try:
                    return await response.json(content_type=None)
                except Exception:
                    # Сервер вернул HTML или текст вместо JSON (например, при перенаправлении на страницу логина)
                    # Если статус 400 или 404, авторизация не поможет, поэтому не пробуем логиниться
                    if response.status not in (400, 404) and not self.token and await self.login():
                        if self.csrf_token:
                            headers = kwargs.get('headers', {})
                            headers['X-CSRF-Token'] = self.csrf_token
                            headers['Referer'] = self.host
                            headers['Origin'] = self.host
                            headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                            kwargs['headers'] = headers
                        async with session.request(method, url, **kwargs) as retry_response:
                            try:
                                return await retry_response.json(content_type=None)
                            except:
                                return {}
                    return {}
        except Exception as e:
            logging.error(f"XUI API error: {e}")
            return {}

    async def get_status(self):
        paths = [
            "/panel/api/server/status", 
            "/server/status", 
            "/panel/server/status", 
            "/api/server/status"
        ]
        for method in ("POST", "GET"):
            for path in paths:
                res = await self._request(method, path, headers={"Accept": "application/json"})
                if isinstance(res, dict) and res.get('success'):
                    return res.get('obj', {})
        return {}

    async def get_online_clients(self):
        paths = [
            "/panel/api/clients/onlines",
            "/panel/api/inbounds/onlines", 
            "/api/inbounds/onlines", 
            "/xui/API/inbounds/onlines"
        ]
        for path in paths:
            res = await self._request("POST", path, headers={"Accept": "application/json"})
            if isinstance(res, dict) and res.get('success'):
                obj = res.get('obj')
                return obj if obj is not None else []
        return None

    async def get_inbounds(self):
        paths = ["/panel/api/inbounds/list", "/panel/inbound/list", "/xui/API/inbounds", "/api/inbounds/list"]
        for method in ("GET", "POST"):
            for path in paths:
                res = await self._request(method, path, headers={"Accept": "application/json"})
                if isinstance(res, dict) and res.get('success'):
                    return res.get('obj', [])
        return []

    async def add_client(self, inbound_id: int, client_id: str, email: str, total_gb: int = 0, expiry_time: int = 0, limit_ip: int = 0, enable: bool = True):
        import json
        payload = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_id,
                    "email": email,
                    "enable": enable,
                    "limitIp": limit_ip,
                    "totalGB": total_gb,
                    "expiryTime": expiry_time,
                    "tgId": "",
                    "subId": ""
                }]
            })
        }
        res = await self._request("POST", "/panel/api/inbounds/addClient", json=payload, headers={"Accept": "application/json"})
        return isinstance(res, dict) and res.get('success', False)

    async def update_client(self, inbound_id: int, client_id: str, email: str, total_gb: int = 0, expiry_time: int = 0, limit_ip: int = 0, enable: bool = True):
        import json
        payload = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_id,
                    "email": email,
                    "enable": enable,
                    "limitIp": limit_ip,
                    "totalGB": total_gb,
                    "expiryTime": expiry_time,
                    "tgId": "",
                    "subId": ""
                }]
            })
        }
        res = await self._request("POST", f"/panel/api/inbounds/updateClient/{client_id}", json=payload, headers={"Accept": "application/json"})
        return isinstance(res, dict) and res.get('success', False)

    async def delete_client(self, inbound_id: int, client_id: str):
        res = await self._request("POST", f"/panel/api/inbounds/{inbound_id}/delClient/{client_id}", headers={"Accept": "application/json"})
        return isinstance(res, dict) and res.get('success', False)

    def get_base_host(self):
        """Извлекает IP или домен из XUI_HOST"""
        from modules.xui.links import get_base_host as _get_base_host
        return _get_base_host(self.host)

    def get_client_links(self, inbound: dict, client: dict):
        """Генерирует ссылки для подключения (VLESS, VMess, Trojan, Shadowsocks)"""
        from modules.xui.links import get_client_links as _get_client_links
        return _get_client_links(inbound, client, self.host)

    async def get_client_links_api(self, inbound_id: int, email: str):
        """Получает готовые ссылки для клиента напрямую через встроенное API панели 3X-UI"""
        res = await self._request("GET", f"/panel/api/inbounds/getClientLinks/{inbound_id}/{email}", headers={"Accept": "application/json"})
        if isinstance(res, dict) and res.get('success'):
            return res.get('obj', [])
        return []


xui = XuiClient()
