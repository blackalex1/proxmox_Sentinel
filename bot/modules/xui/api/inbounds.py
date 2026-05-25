from .clients import XuiClientClients

class XuiClient(XuiClientClients):
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
