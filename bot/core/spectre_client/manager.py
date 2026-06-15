import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from core.config import settings
from .client import SpectrePanelInstance, probe_panel_url, normalize_url, parse_env_content

logger = logging.getLogger(__name__)


async def _discover_panel_config(run_cmd, candidate_paths: List[str]) -> Optional[Tuple[dict, str]]:
    """
    Универсальный процесс поиска файла конфигурации .env на инстансе (LXC или VPS).
    run_cmd - асинхронная функция, принимающая список аргументов команды и возвращающая (success, stdout)
    """
    # 1. Сначала пробуем получить путь через systemd-сервис spectre-agent
    service_path = None
    try:
        success_svc, stdout_svc = await run_cmd(["systemctl", "show", "-p", "WorkingDirectory", "spectre-agent"])
        if success_svc and stdout_svc:
            svc_out = stdout_svc.strip()
            if svc_out.startswith("WorkingDirectory=") and len(svc_out) > 17:
                work_dir = svc_out.split("=", 1)[1].strip()
                if work_dir.endswith("/host") or work_dir.endswith("\\host"):
                    proj_dir = work_dir[:-5]
                else:
                    proj_dir = work_dir
                service_path = f"{proj_dir.rstrip('/')}/config/.env"
    except Exception:
        pass

    # 2. Динамический поиск файлов config/.env с помощью find
    detected_paths = []
    try:
        success_find, stdout_find = await run_cmd(["find", "/opt", "/root", "/home", "/app", "/var", "-maxdepth", "4", "-name", ".env"])
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
    
    # Если динамические методы не дали результатов, используем резервный список путей
    if not paths_to_check:
        paths_to_check = list(candidate_paths)

    for path in paths_to_check:
        try:
            success, stdout = await run_cmd(["cat", path])
            if success and stdout:
                config = parse_env_content(stdout)
                if config.get("PANEL_PORT") and config.get("API_TOKEN"):
                    return config, path
        except Exception:
            pass
    return None


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
        logging.info("spectre_discovery_starting_panel_autodiscovery")
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

        async def discover_lxc_panel(node_name, vm):
            vmid = vm['vmid']
            try:
                async def run_lxc_cmd(cmd: List[str]) -> Tuple[bool, str]:
                    full_cmd = ["pct", "exec", str(vmid), "--"] + cmd
                    proc = await asyncio.create_subprocess_exec(
                        *full_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    stdout, _ = await proc.communicate()
                    return proc.returncode == 0, stdout.decode('utf-8', errors='ignore')

                res = await _discover_panel_config(run_lxc_cmd, candidate_paths)
                if res:
                    config, path = res
                    port = config.get("PANEL_PORT")
                    token = config.get("API_TOKEN")
                    secret_path = config.get("PANEL_SECRET_PATH", "ui")
                    
                    if port and token:
                        from modules.proxmox.api import proxmox
                        ip = proxmox.get_lxc_ip(node_name, vmid)
                        if ip:
                            url = await probe_panel_url(ip, port)
                            # Избегаем дубликатов
                            is_dup = False
                            norm_url = normalize_url(url)
                            for ep in new_panels.values():
                                norm_ep = normalize_url(ep.url)
                                if norm_ep and norm_url and norm_ep == norm_url:
                                    is_dup = True
                                    break
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
                                    identifier=str(vmid),
                                    env_path=path
                                )
                                logging.info("spectre_discovery_naydena_lokalnaya_panel", new_panels[key].name, url)
            except Exception as e:
                logging.error("spectre_discovery_error_searching_in_lxc", vmid, e)

        async def discover_vps_panel(server):
            vps_ip = server['ip']
            try:
                from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
                async def run_vps_cmd(cmd: List[str]) -> Tuple[bool, str]:
                    success, stdout, _ = await run_remote_ssh_cmd(server, cmd)
                    return success, stdout

                res = await _discover_panel_config(run_vps_cmd, candidate_paths)
                if res:
                    config, path = res
                    port = config.get("PANEL_PORT")
                    token = config.get("API_TOKEN")
                    secret_path = config.get("PANEL_SECRET_PATH", "ui")
                    
                    if port and token:
                        url = await probe_panel_url(vps_ip, port)
                        # Избегаем дубликатов
                        is_dup = False
                        norm_url = normalize_url(url)
                        for ep in new_panels.values():
                            norm_ep = normalize_url(ep.url)
                            if norm_ep and norm_url and norm_ep == norm_url:
                                    is_dup = True
                                    break
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
                                identifier=vps_ip,
                                env_path=path
                            )
                            logging.info("spectre_discovery_naydena_udalennaya_panel", new_panels[key].name, url)
            except Exception as e:
                logging.error("spectre_discovery_error_searching_on_remote_vps", vps_ip, e)

        # Собираем все асинхронные задачи поиска
        tasks = []

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
                            tasks.append(discover_lxc_panel(node_name, vm))
            except Exception as e:
                logging.error("spectre_discovery_error_searching_in_proxmox", e)

        # 2. Поиск на удаленных серверах VPS
        if settings.remote_monitor_enable and settings.remote_servers:
            for server in settings.remote_servers:
                tasks.append(discover_vps_panel(server))

        # Запускаем все задачи автообнаружения параллельно
        if tasks:
            await asyncio.gather(*tasks)

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
                    norm_url = normalize_url(url)
                    for ep in new_panels.values():
                        norm_ep = normalize_url(ep.url)
                        if norm_ep and norm_url and norm_ep == norm_url:
                            is_dup = True
                            break
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
                        logging.info("spectre_discovery_dobavlena_ruchnaya_panel", name, url)

        async with self._lock:
            self.panels = new_panels
        logging.info("spectre_discovery_avtoobnaruzhenie_zaversheno_naydeno_paneley", len(self.panels))
        
    async def start_discovery_loop(self):
        """Фоновый периодический запуск поиска новых панелей раз в 5 минут."""
        while True:
            try:
                await self.discover_panels()
            except Exception as e:
                logging.error("spectre_discovery_error_in_autodiscovery_loop", e)
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
                    logging.info("spectre_panel_forwarded_investigation_report_to_master", p.name)
                    return True
                elif success and not res.get("reported"):
                    logging.debug("spectre_panel_is_not_a_slave_skipping", p.name)
            except Exception as e:
                logging.error("spectre_error_sending_report_via", p.name, e)
        
        logging.debug("spectre_ni_odna_panel_ne_yavlyaetsya_sleyvom")
        return False


spectre_manager = SpectreClientManager()
