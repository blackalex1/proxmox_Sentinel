import aiohttp
import logging
from core.config import settings

class XuiClientBase:
    def __init__(self):
        self.host = settings.xui_host.rstrip('/') if settings.xui_host else ""
        self.username = settings.xui_username
        self.password = settings.xui_password
        self.token = settings.xui_api_token
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

    def get_base_host(self):
        """Извлекает IP или домен из XUI_HOST"""
        from modules.xui.links import get_base_host as _get_base_host
        return _get_base_host(self.host)
