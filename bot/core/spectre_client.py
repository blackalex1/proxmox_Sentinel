import asyncio
import logging
import aiohttp
from typing import Dict, List, Optional, Tuple

from core.config import settings

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
                    logging.info(f"[Spectre Discovery] Панель ответила по протоколу {proto} на {url} (статус {response.status})")
                    return url
            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError):
                continue
            except Exception:
                continue
    return f"https://{ip}:{port}"

class SpectrePanelInstance:
    """
    Представляет инстанс Spectre Panel (локальный LXC или удаленный VPS).
    """
    def __init__(self, name: str, url: str, token: str, secret_path: str, source_type: str, identifier: str):
        self.name = name
        self.url = url.rstrip('/')
        self.token = token
        self.secret_path = secret_path.strip('/')
        self.source_type = source_type # 'lxc' или 'vps'
        self.identifier = identifier   # VMID для LXC, IP для VPS
        
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
                        logging.warning(f"[Spectre API {self.name}] Ошибка {response.status}: {text[:200]}")
                        return False, {"error": f"HTTP {response.status}", "details": text}
        except Exception as e:
            logging.error(f"[Spectre API {self.name}] Исключение при запросе: {e}")
            return False, {"error": str(e)}

    async def get_audit_logs(self, limit: int = 10) -> Tuple[bool, dict]:
        """Запрашивает последние записи логов аудита с панели."""
        return await self.request("GET", "/api/security/audit-logs", params={"limit": limit})

class SpectreClientManager:
    """
    Менеджер для автоматического поиска и управления панелями Spectre Panel.
    """
    def __init__(self):
        self.panels: Dict[str, SpectrePanelInstance] = {}
        self._lock = asyncio.Lock()
        
    def get_panel_by_vmid(self, vmid: int) -> Optional[SpectrePanelInstance]:
        """Возвращает панель, запущенную в LXC с указанным VMID."""
        for p in self.panels.values():
            if p.source_type == 'lxc' and str(p.identifier) == str(vmid):
                return p
        return None
        
    def get_panel_by_vps_ip(self, ip: str) -> Optional[SpectrePanelInstance]:
        """Возвращает панель, запущенную на удаленном VPS с указанным IP."""
        for p in self.panels.values():
            if p.source_type == 'vps' and str(p.identifier) == str(ip):
                return p
        return None

    async def discover_panels(self):
        """
        Производит автоматический поиск Spectre Panel на Proxmox LXC и удаленных VPS.
        """
        logging.info("[Spectre Discovery] Запуск автообнаружения панелей...")
        new_panels = {}
        candidate_paths = [
            "/opt/vpn_panel/config/.env",
            "/opt/spectre-panel/config/.env",
            "/root/Spectre-panel/config/.env",
            "/root/panel/config/.env",
            "/home/spectre-panel/config/.env",
            "/app/config/.env",
            "/opt/Spectre-panel/config/.env"
        ]
        
        # 1. Поиск на локальных LXC-контейнерах
        if settings.proxmox_host:
            try:
                from modules.proxmox.api import proxmox
                nodes = proxmox.get_nodes()
                for node in nodes:
                    node_name = node['node']
                    vms = proxmox.get_vms(node_name)
                    for vm in vms:
                        if vm.get('type') == 'lxc' and vm.get('status') == 'running':
                            vmid = vm['vmid']
                            
                            # Сначала пробуем получить путь через systemd-сервис vpn-host-agent
                            service_path = None
                            try:
                                cmd_svc = ["pct", "exec", str(vmid), "--", "systemctl", "show", "-p", "WorkingDirectory", "vpn-host-agent"]
                                proc_svc = await asyncio.create_subprocess_exec(
                                    *cmd_svc,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.DEVNULL
                                )
                                stdout_svc, _ = await proc_svc.communicate()
                                if proc_svc.returncode == 0 and stdout_svc:
                                    svc_out = stdout_svc.decode('utf-8', errors='ignore').strip()
                                    if svc_out.startswith("WorkingDirectory=") and len(svc_out) > 17:
                                        work_dir = svc_out.split("=", 1)[1].strip()
                                        if work_dir.endswith("/host"):
                                            proj_dir = work_dir[:-5]
                                        elif work_dir.endswith("\\host"):
                                            proj_dir = work_dir[:-5]
                                        else:
                                            proj_dir = work_dir
                                        
                                        service_path = f"{proj_dir.rstrip('/')}/config/.env"
                            except Exception:
                                pass
                                
                            # Динамический поиск файлов config/.env внутри контейнера с помощью find
                            detected_paths = []
                            try:
                                find_cmd = ["pct", "exec", str(vmid), "--", "find", "/opt", "/root", "/home", "/app", "/var", "-maxdepth", "4", "-name", ".env"]
                                find_proc = await asyncio.create_subprocess_exec(
                                    *find_cmd,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.DEVNULL
                                )
                                find_stdout, _ = await find_proc.communicate()
                                if find_proc.returncode == 0 and find_stdout:
                                    for found_path in find_stdout.decode('utf-8', errors='ignore').splitlines():
                                        found_path = found_path.strip()
                                        if found_path.endswith('/config/.env') and found_path not in detected_paths:
                                            detected_paths.append(found_path)
                            except Exception:
                                pass

                            paths_to_check = list(detected_paths)
                            if service_path and service_path not in paths_to_check:
                                paths_to_check.append(service_path)
                            for c_path in candidate_paths:
                                if c_path not in paths_to_check:
                                    paths_to_check.append(c_path)
                                
                            # Проверяем наличие файла .env
                            for path in paths_to_check:
                                cmd = ["pct", "exec", str(vmid), "--", "cat", path]
                                proc = await asyncio.create_subprocess_exec(
                                    *cmd,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.DEVNULL
                                )
                                stdout, _ = await proc.communicate()
                                if proc.returncode == 0 and stdout:
                                    env_content = stdout.decode('utf-8', errors='ignore')
                                    config = parse_env_content(env_content)
                                    
                                    port = config.get("PANEL_PORT")
                                    token = config.get("API_TOKEN")
                                    secret_path = config.get("PANEL_SECRET_PATH", "ui")
                                    
                                    if port and token:
                                        ip = proxmox.get_lxc_ip(node_name, vmid)
                                        if ip:
                                            url = await probe_panel_url(ip, port)
                                            # Избегаем дубликатов
                                            is_dup = False
                                            for ep in new_panels.values():
                                                if ep.url.rstrip('/').lower() == url.rstrip('/').lower():
                                                    is_dup = True
                                                    break
                                            if not is_dup:
                                                key = f"lxc_{vmid}"
                                                new_panels[key] = SpectrePanelInstance(
                                                    name=f"LXC {vmid} ({vm.get('name', 'VPN')})",
                                                    url=url,
                                                    token=token,
                                                    secret_path=secret_path,
                                                    source_type="lxc",
                                                    identifier=str(vmid)
                                                )
                                                logging.info(f"[Spectre Discovery] Найдена локальная панель: {new_panels[key].name} ({url})")
                                            break
            except Exception as e:
                logging.error(f"[Spectre Discovery] Ошибка при поиске в Proxmox: {e}")
                
        # 2. Поиск на удаленных серверах VPS
        if settings.remote_servers:
            from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
            for server in settings.remote_servers:
                vps_ip = server['ip']
                try:
                    # Сначала пробуем получить путь через systemd-сервис vpn-host-agent на удаленном VPS
                    service_path = None
                    try:
                        success_svc, stdout_svc, _ = await run_remote_ssh_cmd(server, ["systemctl", "show", "-p", "WorkingDirectory", "vpn-host-agent"])
                        if success_svc and stdout_svc:
                            svc_out = stdout_svc.strip()
                            if svc_out.startswith("WorkingDirectory=") and len(svc_out) > 17:
                                work_dir = svc_out.split("=", 1)[1].strip()
                                if work_dir.endswith("/host"):
                                    proj_dir = work_dir[:-5]
                                elif work_dir.endswith("\\host"):
                                    proj_dir = work_dir[:-5]
                                else:
                                    proj_dir = work_dir
                                
                                service_path = f"{proj_dir.rstrip('/')}/config/.env"
                    except Exception:
                        pass
                        
                    # Динамический поиск файлов config/.env на удаленном VPS с помощью find
                    detected_paths = []
                    try:
                        success_find, stdout_find, _ = await run_remote_ssh_cmd(
                            server, 
                            ["find", "/opt", "/root", "/home", "/app", "/var", "-maxdepth", "4", "-name", ".env"]
                        )
                        if success_find and stdout_find:
                            for found_path in stdout_find.splitlines():
                                found_path = found_path.strip()
                                if found_path.endswith('/config/.env') and found_path not in detected_paths:
                                    detected_paths.append(found_path)
                    except Exception:
                        pass

                    paths_to_check = list(detected_paths)
                    if service_path and service_path not in paths_to_check:
                        paths_to_check.append(service_path)
                    for c_path in candidate_paths:
                        if c_path not in paths_to_check:
                            paths_to_check.append(c_path)
                        
                    for path in paths_to_check:
                        # Проверяем файл .env через SSH
                        success, stdout, stderr = await run_remote_ssh_cmd(server, ["cat", path])
                        if success and stdout:
                            config = parse_env_content(stdout)
                            port = config.get("PANEL_PORT")
                            token = config.get("API_TOKEN")
                            secret_path = config.get("PANEL_SECRET_PATH", "ui")
                            
                            if port and token:
                                url = await probe_panel_url(vps_ip, port)
                                # Избегаем дубликатов
                                is_dup = False
                                for ep in new_panels.values():
                                    if ep.url.rstrip('/').lower() == url.rstrip('/').lower():
                                        is_dup = True
                                        break
                                if not is_dup:
                                    key = f"vps_{vps_ip}"
                                    new_panels[key] = SpectrePanelInstance(
                                        name=f"VPS {vps_ip}",
                                        url=url,
                                        token=token,
                                        secret_path=secret_path,
                                        source_type="vps",
                                        identifier=vps_ip
                                    )
                                    logging.info(f"[Spectre Discovery] Найдена удаленная панель: {new_panels[key].name} ({url})")
                                break
                except Exception as e:
                    logging.error(f"[Spectre Discovery] Ошибка при поиске на удаленном VPS {vps_ip}: {e}")
                    
        # 3. Добавление панелей, настроенных вручную в .env
        if settings.spectre_panels:
            for idx, p in enumerate(settings.spectre_panels):
                url = p.get("url")
                token = p.get("token")
                if url and token:
                    # Пробуем распарсить url и динамически проверить протокол (HTTP/HTTPS)
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        host = parsed.hostname
                        port = parsed.port
                        if host and port:
                            url = await probe_panel_url(host, str(port))
                    except Exception:
                        pass
                        
                    # Избегаем дубликатов
                    is_dup = False
                    for ep in new_panels.values():
                        if ep.url.rstrip('/').lower() == url.rstrip('/').lower():
                            is_dup = True
                            break
                    if not is_dup:
                        name = p.get("name", f"Manual Panel {idx+1}")
                        secret_path = p.get("secret_path", "ui")
                        key = f"manual_{idx}"
                        new_panels[key] = SpectrePanelInstance(
                            name=name,
                            url=url,
                            token=token,
                            secret_path=secret_path,
                            source_type="manual",
                            identifier=str(idx)
                        )
                        logging.info(f"[Spectre Discovery] Добавлена ручная панель: {name} ({url})")

        async with self._lock:
            self.panels = new_panels
        logging.info(f"[Spectre Discovery] Автообнаружение завершено. Найдено панелей: {len(self.panels)}")
        
    async def start_discovery_loop(self):
        """Фоновый периодический запуск поиска новых панелей раз в 5 минут."""
        while True:
            try:
                await self.discover_panels()
            except Exception as e:
                logging.error(f"[Spectre Discovery] Ошибка в цикле автообнаружения: {e}")
            await asyncio.sleep(300)

    # --- Высокоуровневые API для взаимодействия с панелями ---

    async def get_client_by_connection(self, client_ip: Optional[str], dst_ip: Optional[str], port: int, source_type: str, source_id: str) -> Optional[Tuple[str, SpectrePanelInstance, str]]:
        """
        Ищет email клиента, обращаясь к эндпоинту соответствующей панели.
        Возвращает кортеж (email, panel, source) или None.
        """
        panel = None
        if source_type == 'lxc':
            panel = self.get_panel_by_vmid(int(source_id))
        elif source_type == 'vps':
            panel = self.get_panel_by_vps_ip(source_id)
            
        params = {"port": port}
        if client_ip:
            params["client_ip"] = client_ip
        if dst_ip:
            params["dst_ip"] = dst_ip

        # 1. Сначала опрашиваем целевую панель, на которой зафиксировано событие
        if panel:
            success, res = await panel.request("GET", "/api/security/client-by-connection", params=params)
            if success and res.get("success"):
                return res["email"], panel, res.get("source", "xray")
                
        # 2. Резервный поиск (Fallback): опрашиваем все остальные панели.
        # Это необходимо, если client зашел через одну панель (Xray), а трафик вышел
        # наружу через другую по внутреннему туннелю (например, Xray -> Hysteria -> VPS).
        for p in self.panels.values():
            if panel and p.name == panel.name:
                continue
            success, res = await p.request("GET", "/api/security/client-by-connection", params=params)
            if success and res.get("success"):
                return res["email"], p, res.get("source", "xray")
                
        return None


    async def disable_client_everywhere(self, email: str) -> List[Tuple[str, bool, str]]:
        """
        Блокирует клиента и сбрасывает сессии на ВСЕХ обнаруженных панелях.
        Возвращает список результатов: (имя_панели, успешно_ли, сообщение)
        """
        results = []
        for p in self.panels.values():
            success, res = await p.request("POST", "/api/security/disable-client", data={"email": email})
            msg = res.get("msg", "OK" if success else "Ошибка соединения")
            results.append((p.name, success and res.get("success", False), msg))
        return results

    async def enable_client_everywhere(self, email: str) -> List[Tuple[str, bool, str]]:
        """
        Разблокирует клиента на ВСЕХ обнаруженных панелях.
        Возвращает список результатов: (имя_панели, успешно_ли, сообщение)
        """
        results = []
        for p in self.panels.values():
            success, res = await p.request("POST", "/api/security/enable-client", data={"email": email})
            msg = res.get("msg", "OK" if success else "Ошибка соединения")
            results.append((p.name, success and res.get("success", False), msg))
        return results


    async def search_client_all(self, key: str) -> List[dict]:
        """
        Ищет клиента на всех панелях.
        """
        results = []
        for p in self.panels.values():
            success, res = await p.request("GET", "/api/security/search-client", params={"key": key})
            if success and res.get("success"):
                for item in res.get("clients", []):
                    item["panel_name"] = p.name
                    item["panel_url"] = p.url
                    item["panel_secret"] = p.secret_path
                    results.append(item)
        return results

    async def report_investigation_to_master(self, action: str, culprit_email: str, 
                                              tunnel_email: str, details: str):
        """
        Просит каждую свою панель переслать отчёт о расследовании мастер-панели.
        Панели без node_config.json (не слейвы) вернут reported=false и будут пропущены.
        Первая панель-слейв, успешно отправившая отчёт, прерывает цикл.
        """
        for p in self.panels.values():
            try:
                success, res = await p.request("POST", "/api/security/report-to-master", json={
                    "action": action,
                    "client_email": culprit_email,
                    "tunnel_email": tunnel_email,
                    "details": details
                })
                if success and res.get("reported"):
                    logging.info(f"[Spectre] Панель {p.name} переслала отчёт о расследовании мастер-панели")
                    return True
                elif success and not res.get("reported"):
                    logging.debug(f"[Spectre] Панель {p.name} не является слейвом, пропускаем")
            except Exception as e:
                logging.error(f"[Spectre] Ошибка при отправке отчёта через {p.name}: {e}")
        
        logging.debug("[Spectre] Ни одна панель не является слейвом — отчёт не отправлен (это нормально для мастер-бота)")
        return False

# Создаем глобальный синглтон менеджера
spectre_manager = SpectreClientManager()
