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
        try:
            session = await self.get_session()
            url = f"{self.host}/login"
            payload = {"username": self.username, "password": self.password}
            async with session.post(url, data=payload) as response:
                result = await response.json()
                if result.get('success'):
                    return True
                else:
                    logging.error(f"XUI Login failed: {result.get('msg')}")
                    return False
        except Exception as e:
            logging.error(f"XUI Login error: {e}")
            return False

    async def _request(self, method, endpoint, **kwargs):
        if not self.host: return {}
        session = await self.get_session()
        
        # Добавляем Bearer Token в заголовки, если он настроен
        headers = kwargs.get('headers', {})
        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"
        kwargs['headers'] = headers
        
        # Если токена нет, то первая попытка и куки отсутствуют -> логинимся
        if not self.token and not session.cookie_jar:
            await self.login()
            
        url = f"{self.host}{endpoint}"
        try:
            async with session.request(method, url, **kwargs) as response:
                # Пытаемся авторизоваться заново при ошибке 401/400 или 404 (когда возвращает HTML вместо API JSON)
                if response.status in (401, 400, 404) and not self.token:
                    if await self.login():
                        async with session.request(method, url, **kwargs) as retry_response:
                            try:
                                return await retry_response.json()
                            except:
                                return {}
                    return {}
                
                try:
                    return await response.json()
                except Exception:
                    # Сервер вернул HTML или текст вместо JSON (например, при 404 Not Found)
                    # Если произошла проблема с авторизацией, куки могли устареть
                    if not self.token and await self.login():
                        async with session.request(method, url, **kwargs) as retry_response:
                            try:
                                return await retry_response.json()
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
        paths = ["/panel/api/inbounds/onlines", "/api/inbounds/onlines", "/xui/API/inbounds/onlines"]
        for path in paths:
            res = await self._request("POST", path, headers={"Accept": "application/json"})
            if isinstance(res, dict) and res.get('success'):
                return res.get('obj', [])
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
        if not self.host: return ""
        parsed = urlparse(self.host)
        return parsed.hostname or ""

    def get_client_links(self, inbound: dict, client: dict):
        """Генерирует ссылки для подключения (VLESS, VMess, Trojan)"""
        protocol = inbound.get('protocol')
        port = inbound.get('port')
        remark = inbound.get('remark', 'VPN')
        host = self.get_base_host()
        
        client_email = client.get('email', 'client')
        display_name = f"{remark}-{client_email}"
        
        # Парсим настройки
        try:
            settings = json.loads(inbound.get('settings', '{}'))
            stream_settings = json.loads(inbound.get('streamSettings', '{}'))
        except:
            return []

        security = stream_settings.get('security', 'none')
        network = stream_settings.get('network', 'tcp')
        
        links = []

        if protocol == 'vless':
            uid = client.get('id')
            flow = client.get('flow', '')
            
            params = [
                f"type={network}",
                f"security={security}"
            ]
            
            if flow:
                params.append(f"flow={flow}")
                
            if security == 'reality':
                reality_settings = stream_settings.get('realitySettings', {})
                # Некоторые версии 3x-ui хранят настройки внутри 'settings'
                inner_settings = reality_settings.get('settings', {})
                
                fp = inner_settings.get('fingerprint') or reality_settings.get('fingerprint', 'chrome')
                pbk = inner_settings.get('publicKey') or reality_settings.get('publicKey', '')
                sni = inner_settings.get('serverName') or reality_settings.get('serverName') or (reality_settings.get('serverNames', [''])[0])
                spx = inner_settings.get('spiderX') or reality_settings.get('spiderX', '/')
                
                params.append(f"fp={fp}")
                params.append(f"pbk={pbk}")
                if sni: params.append(f"sni={sni}")
                
                short_ids = reality_settings.get('shortIds', [])
                if short_ids: params.append(f"sid={short_ids[0]}")
                
                if spx: params.append(f"spx={quote(spx, safe='')}")
            
            elif security == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                sni = tls_settings.get('serverName')
                if sni: params.append(f"sni={sni}")
                # Дополнительные параметры TLS можно добавить здесь

            if network == 'ws':
                ws_settings = stream_settings.get('wsSettings', {})
                path = ws_settings.get('path', '/')
                params.append(f"path={quote(path, safe='')}")
                ws_host = ws_settings.get('headers', {}).get('Host')
                if ws_host: params.append(f"host={ws_host}")

            query = "&".join(params)
            link = f"vless://{uid}@{host}:{port}?{query}#{quote(display_name)}"
            links.append(link)

        elif protocol == 'vmess':
            uid = client.get('id')
            aid = client.get('aid', 0)
            
            vmess_obj = {
                "v": "2",
                "ps": display_name,
                "add": host,
                "port": port,
                "id": uid,
                "aid": aid,
                "scy": "auto",
                "net": network,
                "type": "none",
                "host": "",
                "path": "",
                "tls": security if security in ('tls', 'reality') else "none",
                "sni": "",
                "fp": ""
            }
            
            if security == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                vmess_obj["sni"] = tls_settings.get('serverName', '')
            elif security == 'reality':
                reality_settings = stream_settings.get('realitySettings', {})
                vmess_obj["sni"] = reality_settings.get('serverName') or (reality_settings.get('serverNames', [''])[0])
                vmess_obj["fp"] = reality_settings.get('fingerprint', 'chrome')

            if network == 'ws':
                ws_settings = stream_settings.get('wsSettings', {})
                vmess_obj["path"] = ws_settings.get('path', '/')
                vmess_obj["host"] = ws_settings.get('headers', {}).get('Host', '')

            json_str = json.dumps(vmess_obj)
            b64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            links.append(f"vmess://{b64_str}")

        elif protocol == 'trojan':
            password = client.get('password')
            
            params = [f"security={security}"]
            if security == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                sni = tls_settings.get('serverName')
                if sni: params.append(f"sni={sni}")
            
            query = "&".join(params)
            link = f"trojan://{password}@{host}:{port}?{query}#{quote(display_name)}"
            links.append(link)

        elif protocol in ('shadowsocks', 'ss'):
            method = settings.get('method') or client.get('method', 'aes-256-gcm')
            password = client.get('password') or client.get('secret') or settings.get('password', '')
            
            # Base64 encode the method:password credentials for the standard ss:// link
            credentials = f"{method}:{password}"
            b64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            
            link = f"ss://{b64_credentials}@{host}:{port}#{quote(display_name)}"
            links.append(link)

        return links

    async def get_client_links_api(self, inbound_id: int, email: str):
        """Получает готовые ссылки для клиента напрямую через встроенное API панели 3X-UI"""
        res = await self._request("GET", f"/panel/api/inbounds/getClientLinks/{inbound_id}/{email}", headers={"Accept": "application/json"})
        if isinstance(res, dict) and res.get('success'):
            return res.get('obj', [])
        return []


xui = XuiClient()
