import asyncio
import re
import logging
from core.config import settings

async def get_and_kill_local_or_lxc_process(vmid, spt):
    """
    Находит и убивает процесс по порту источника.
    Если vmid == 0, ищет локально на хосте Proxmox.
    Если vmid > 0, ищет и убивает процесс внутри LXC контейнера с помощью 'pct exec'.
    Возвращает кортеж (proc_name, pid) в случае успеха, иначе (None, None).
    """
    try:
        if vmid == 0:
            cmd = ["ss", "-atnup"]
            logging.info("local_ips_running_command", ' '.join(cmd))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            logging.info("local_ips_vyvod_ss_pervykh_500_simvolov", stdout[:500])
            
            matched = False
            for line in stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[4].endswith(f":{spt}"):
                    matched = True
                    logging.info("local_ips_found_match_line_port", spt, line.strip())
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        
                        # Самозащита (suicide prevention): проверяем, не является ли процесс самим ботом или его ребенком
                        import os
                        is_self_or_child = False
                        try:
                            target_pid = int(pid)
                            if target_pid == os.getpid():
                                is_self_or_child = True
                            else:
                                # Проверяем временный белый список командной строки
                                if getattr(settings, 'ips_temp_whitelist_cmdline', None):
                                    cmdline_path = f"/proc/{target_pid}/cmdline"
                                    if os.path.exists(cmdline_path):
                                        try:
                                            with open(cmdline_path, "r") as f:
                                                cmdline = f.read()
                                            if settings.ips_temp_whitelist_cmdline in cmdline:
                                                is_self_or_child = True
                                        except Exception:
                                            pass
                                
                                # Проверяем родительский PID в /proc
                                if not is_self_or_child:
                                    status_path = f"/proc/{target_pid}/status"
                                    if os.path.exists(status_path):
                                        with open(status_path, "r") as f:
                                            for status_line in f:
                                                if status_line.startswith("PPid:"):
                                                    ppid = int(status_line.split()[1])
                                                    if ppid == os.getpid():
                                                        is_self_or_child = True
                                                    break
                        except Exception:
                            pass
                            
                        if is_self_or_child:
                            logging.info("local_ips_protsess_pid_yavlyaetsya_samim_botom", proc_name, pid)
                            return proc_name, "WHITELISTED"
                            
                        node = "local"
                        from core.db import is_whitelisted
                        if proc_name.lower().strip() in settings.ips_process_whitelist or await is_whitelisted(node, process=proc_name):
                            logging.info("local_ips_protsess_pid_na_khoste_v", proc_name, pid)
                            return proc_name, "WHITELISTED"
                        
                        kill_proc = await asyncio.create_subprocess_exec(
                            "kill", "-9", pid,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info("local_ips_process_pid_host_port_successfully_terminated", proc_name, pid, spt)
                        return proc_name, pid
            if not matched:
                logging.warning("local_ips_no_connection_to_port_found", spt)
        else:
            cmd = ["pct", "exec", str(vmid), "--", "ss", "-atnup"]
            logging.info("lxc_ips_running_command", ' '.join(cmd))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            logging.info("lxc_ips_vyvod_ss_v_lxc_pervykh", vmid, stdout[:500])
            
            matched = False
            for line in stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[4].endswith(f":{spt}"):
                    matched = True
                    logging.info("lxc_ips_found_match_line_lxc_port", vmid, spt, line.strip())
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        node = f"lxc_{vmid}"
                        from core.db import is_whitelisted
                        if proc_name.lower().strip() in settings.ips_process_whitelist or await is_whitelisted(node, process=proc_name):
                            logging.info("lxc_ips_protsess_pid_v_lxc_v", proc_name, pid, vmid)
                            return proc_name, "WHITELISTED"
                        
                        kill_cmd = ["pct", "exec", str(vmid), "--", "kill", "-9", pid]
                        kill_proc = await asyncio.create_subprocess_exec(
                            *kill_cmd,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info("lxc_ips_process_pid_inside_lxc_port_successfully", proc_name, pid, vmid, spt)
                        return proc_name, pid
            if not matched:
                logging.warning("lxc_ips_no_connection_to_port_inside", spt, vmid)
    except Exception as e:
        logging.error("lxc_local_ips_error_searching_and_killing", e)
    return None, None
