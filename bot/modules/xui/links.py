import json
import base64
from urllib.parse import urlparse, quote

def get_base_host(host_url: str) -> str:
    """Извлекает IP или домен из XUI_HOST"""
    if not host_url:
        return ""
    parsed = urlparse(host_url)
    return parsed.hostname or ""

def get_client_links(inbound: dict, client: dict, host_url: str) -> list:
    """Генерирует ссылки для подключения (VLESS, VMess, Trojan, Shadowsocks)"""
    protocol = inbound.get('protocol')
    port = inbound.get('port')
    remark = inbound.get('remark', 'VPN')
    host = get_base_host(host_url)
    
    client_email = client.get('email', 'client')
    display_name = f"{remark}-{client_email}"
    
    # Парсим настройки
    try:
        settings = json.loads(inbound.get('settings', '{}'))
        stream_settings = json.loads(inbound.get('streamSettings', '{}'))
    except Exception:
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
        
        credentials = f"{method}:{password}"
        b64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        link = f"ss://{b64_credentials}@{host}:{port}#{quote(display_name)}"
        links.append(link)

    return links
