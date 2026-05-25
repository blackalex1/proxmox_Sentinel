import json
from .base import XuiClientBase

class XuiClientClients(XuiClientBase):
    async def add_client(self, inbound_id: int, client_id: str, email: str, total_gb: int = 0, expiry_time: int = 0, limit_ip: int = 0, enable: bool = True):
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
