import ctypes
import json
import logging
import os
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

_SENTINEL_LIB: Optional[ctypes.CDLL] = None
_SENTINEL_LIB_TRIED: bool = False


def _get_sentinel_core_bin() -> str:
    """Finds the sentinel-core binary across standard relative and system paths."""
    import shutil
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # bot/
    project_root = os.path.dirname(base_dir)  # controller/

    is_windows = sys.platform == "win32" or os.name == "nt"
    bin_name = "sentinel-core.exe" if is_windows else "sentinel-core"

    candidate_paths = [
        os.path.join(base_dir, "bin", bin_name),
        os.path.join(project_root, "bin", bin_name),
        "/usr/local/bin/sentinel-core",
        "/usr/bin/sentinel-core",
        "/opt/sentinel-core/bin/sentinel-core",
        os.path.join(os.path.dirname(project_root), "sentinel_core", bin_name),
        os.path.join(os.path.dirname(project_root), "sentinel_core", "dist", bin_name),
        os.path.join(os.path.dirname(project_root), "sentinel_core", "bin", bin_name),
        os.path.join(os.path.dirname(project_root), "panel", "bin", bin_name),
        os.path.join(os.path.dirname(project_root), "sentinel_core", bin_name.replace(".exe", "")),
    ]

    for p in candidate_paths:
        if os.path.isfile(p) and os.path.getsize(p) > 3 * 1024 * 1024:
            if os.name != 'nt' and not os.access(p, os.X_OK):
                try:
                    os.chmod(p, 0o755)
                except Exception:
                    pass
            return p

    which_path = shutil.which(bin_name) or shutil.which("sentinel-core")
    if which_path and os.path.isfile(which_path) and os.path.getsize(which_path) > 3 * 1024 * 1024:
        return which_path

    return os.path.join(base_dir, "bin", bin_name)


def _find_sentinel_core_lib_path() -> Optional[str]:
    """Finds the sentinel-core shared library (.dll, .so, .dylib) on Windows, Linux, or macOS."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(base_dir)

    is_windows = sys.platform == "win32" or os.name == "nt"
    is_darwin = sys.platform == "darwin"

    if is_windows:
        lib_names = ["sentinel-core.dll", "libsentinel-core.dll"]
    elif is_darwin:
        lib_names = ["libsentinel-core.dylib", "sentinel-core.dylib"]
    else:
        lib_names = ["libsentinel-core.so", "sentinel-core.so", "libsentinel_core_16k_arm64.so"]

    candidate_dirs = [
        os.path.join(base_dir, "bin"),
        os.path.join(project_root, "bin"),
        "/usr/local/lib",
        "/usr/lib",
        os.path.join(os.path.dirname(project_root), "sentinel_core"),
        os.path.join(os.path.dirname(project_root), "sentinel_core", "bin"),
        os.path.join(os.path.dirname(project_root), "panel", "bin"),
    ]

    for d in candidate_dirs:
        for name in lib_names:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.path.getsize(p) > 3 * 1024 * 1024:
                return p


    try:
        from ctypes.util import find_library
        sys_lib = find_library("sentinel-core") or find_library("libsentinel-core")
        if sys_lib:
            return sys_lib
    except Exception:
        pass

    return None


def _init_sentinel_lib(lib: Any) -> Any:
    """Configures argtypes and restype for all exported Sentinel C-FFI functions."""
    if hasattr(lib, "SentinelFreeString"):
        try:
            lib.SentinelFreeString.argtypes = [ctypes.c_void_p]
            lib.SentinelFreeString.restype = None
        except (AttributeError, TypeError):
            pass

    func_signatures = [
        ("SentinelGetEngineVersion", []),
        ("SentinelParseIptablesLine", [ctypes.c_char_p, ctypes.c_int]),
        ("SentinelClassifyConnection", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]),
        ("SentinelFindRealVPNClientIP", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p]),
        ("SentinelFindXrayClientEmail", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]),
        ("SentinelFindHysteriaClientEmail", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]),
        ("SentinelFindClientIPForEmail", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]),
        ("SentinelParseAuthLogLine", [ctypes.c_char_p]),
        ("SentinelParseRouterConntrackLine", [ctypes.c_char_p]),
        ("SentinelParseRouterIptablesLine", [ctypes.c_char_p]),
        ("SentinelPing", [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]),
        ("SentinelGetSecuritySchema", [ctypes.c_char_p]),
        ("SentinelParseSubscription", [ctypes.c_char_p]),
        ("SentinelBatchCheckProxies", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
        ("SentinelFindFastestProxy", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
        ("SentinelBuildFailoverClientConfig", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p]),
        ("SentinelSetLanguage", [ctypes.c_char_p]),
    ]

    for name, argtypes in func_signatures:
        if hasattr(lib, name):
            try:
                func = getattr(lib, name)
                func.argtypes = argtypes
                func.restype = ctypes.c_void_p
            except (AttributeError, TypeError):
                pass

    return lib


def get_sentinel_lib() -> Optional[ctypes.CDLL]:
    """Returns the loaded ctypes.CDLL instance for sentinel-core, or None if unavailable."""
    global _SENTINEL_LIB, _SENTINEL_LIB_TRIED
    if _SENTINEL_LIB is not None:
        return _SENTINEL_LIB
    if _SENTINEL_LIB_TRIED:
        return None

    _SENTINEL_LIB_TRIED = True
    lib_path = _find_sentinel_core_lib_path()
    if not lib_path:
        return None

    try:
        lib = ctypes.CDLL(lib_path)
        _init_sentinel_lib(lib)
        _SENTINEL_LIB = lib
        logger.info("sentinel_core_library_loaded", lib_path)
        return _SENTINEL_LIB
    except Exception as e:
        logger.warning("sentinel_core_bridge_call_failed", "load_lib", e)
        return None


def _ffi_call_str(func_name: str, *args) -> Optional[str]:
    """Calls a C-FFI function returning a Go allocated string, decodes utf-8, and frees memory via SentinelFreeString."""
    lib = get_sentinel_lib()
    if not lib or not hasattr(lib, func_name):
        return None

    func = getattr(lib, func_name)
    if hasattr(func, "restype") and func.restype != ctypes.c_void_p and func_name != "SentinelFreeString":
        func.restype = ctypes.c_void_p

    c_args = []
    for a in args:
        if isinstance(a, str):
            c_args.append(a.encode("utf-8"))
        elif isinstance(a, int):
            c_args.append(ctypes.c_int(a))
        elif isinstance(a, bytes):
            c_args.append(a)
        elif a is None:
            c_args.append(None)
        else:
            c_args.append(a)

    ptr = func(*c_args)
    if not ptr:
        return None
    try:
        raw_bytes = ctypes.cast(ptr, ctypes.c_char_p).value
        if raw_bytes is None:
            return None
        return raw_bytes.decode("utf-8", errors="replace")
    finally:
        if hasattr(lib, "SentinelFreeString"):
            lib.SentinelFreeString(ctypes.c_void_p(ptr))


def _ffi_call_json(func_name: str, *args) -> Optional[Any]:
    """Calls a C-FFI function and parses its JSON output."""
    raw = _ffi_call_str(func_name, *args)
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"raw": raw}


def run_core_command(args: List[str], input_data: Optional[str] = None, parse_json: bool = True) -> Any:
    """Executes sentinel-core CLI with given args and returns parsed JSON output or raw string."""
    import shutil
    bin_path = _get_sentinel_core_bin()
    if not os.path.isabs(bin_path) and not os.path.exists(bin_path):
        which_p = shutil.which(bin_path)
        if which_p:
            bin_path = which_p

    if not os.path.exists(bin_path) and not shutil.which(bin_path):
        logger.debug("sentinel-core binary not found at '%s', skipping command", bin_path)
        return {"error": f"sentinel-core binary not found at '{bin_path}'"}

    cmd = [bin_path] + args
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        stdout, stderr = proc.communicate(input=input_data, timeout=10)
        output = (stdout or "").strip()
        if output:
            if not parse_json:
                return output
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return output

        if proc.returncode != 0:
            err_msg = (stderr or "").strip() or f"Process exited with code {proc.returncode}"
            logger.error("sentinel-core exited with code %d: %s", proc.returncode, err_msg)
            return {"error": err_msg}

        return {"raw": output}
    except Exception as e:
        logger.exception("Failed to execute sentinel-core CLI: %s", e)
        return {"error": str(e)}


def parse_iptables_line(line: str, vpn_vmid: int = 100) -> Optional[Dict[str, Any]]:
    """Parses a netfilter/iptables kernel log line via sentinel-core."""
    try:
        res = _ffi_call_json("SentinelParseIptablesLine", line, int(vpn_vmid))
        if isinstance(res, dict) and "proto" in res:
            return res
    except Exception as e:
        logger.debug("FFI parse_iptables_line error: %s", e)

    res = run_core_command(["security", "parse-iptables", "--line", line, "--vmid", str(vpn_vmid)])
    if isinstance(res, dict) and "proto" in res:
        return res
    return None


def classify_connection(
    event: Dict[str, Any],
    policy: Optional[Dict[str, Any]] = None,
    lang: str = "ru"
) -> Tuple[str, str, str]:
    """
    Classifies a network event using sentinel-core security matrix.
    Returns tuple: (risk_level, label, description)
    risk_level is one of: 'INFO', 'WARNING', 'CRITICAL'
    """
    event_json = json.dumps(event)
    policy_json = json.dumps(policy or {})

    try:
        res = _ffi_call_json("SentinelClassifyConnection", event_json, policy_json, lang)
        if isinstance(res, dict) and "risk_level" in res:
            return res.get("risk_level", "INFO"), res.get("label", ""), res.get("description", "")
    except Exception as e:
        logger.debug("FFI classify_connection error: %s", e)

    res = run_core_command(["security", "classify", "--event", event_json, "--policy", policy_json, "--lang", lang])
    if isinstance(res, dict) and "risk_level" in res:
        return res.get("risk_level", "INFO"), res.get("label", ""), res.get("description", "")

    return "INFO", "Неизвестная активность", "Не удалось классифицировать сетевую активность"


def find_real_vpn_client_ip(
    proto: str,
    container_ip: str,
    dst_ip: str,
    sport: int,
    dpt: int,
    conntrack_dump: str = ""
) -> Optional[str]:
    """Resolves the real client IP from conntrack NAT table via sentinel-core."""
    if not conntrack_dump:
        for p in ["/proc/net/nf_conntrack", "/proc/net/ip_conntrack"]:
            try:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        conntrack_dump = f.read()
                        if conntrack_dump:
                            break
            except Exception:
                pass

    if get_sentinel_lib():
        try:
            client_ip = _ffi_call_str("SentinelFindRealVPNClientIP", proto, container_ip, dst_ip, int(sport), int(dpt), conntrack_dump)
            if client_ip:
                return client_ip.strip()
            return None
        except Exception as e:
            logger.debug("FFI find_real_vpn_client_ip error: %s", e)
            return None

    # CLI fallback only if FFI is completely unavailable and payload is not too large
    if conntrack_dump and len(conntrack_dump) > 32768:
        return None

    args = [
        "security", "find-vpn-client",
        "--proto", proto,
        "--container-ip", container_ip,
        "--dst-ip", dst_ip,
        "--sport", str(sport),
        "--dpt", str(dpt),
    ]
    if conntrack_dump:
        args.extend(["--dump", conntrack_dump])

    res = run_core_command(args)
    if isinstance(res, dict) and res.get("client_ip"):
        return res["client_ip"].strip()
    return None


def find_xray_client_email(
    lines: List[str],
    dst_ip: Optional[str],
    dst_port: int,
    client_ip: Optional[str] = None,
    max_age_sec: int = 300
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Searches Xray and Sing-box log lines for client email, IP, and inbound tag via sentinel-core.
    Returns: (email, ip, inbound_tag)
    """
    lines_json = json.dumps(lines)
    if get_sentinel_lib():
        try:
            res = _ffi_call_json("SentinelFindXrayClientEmail", lines_json, client_ip or "", dst_ip or "", int(dst_port), int(max_age_sec))
            if isinstance(res, dict) and res.get("email"):
                return res.get("email"), res.get("ip") or client_ip, res.get("inbound_tag")
            return None, None, None
        except Exception as e:
            logger.debug("FFI find_xray_client_email error: %s", e)
            return None, None, None

    if len(lines_json) > 32768:
        return None, None, None

    args = [
        "security", "find-proxy-client",
        "--core", "xray",
        "--lines", lines_json,
        "--client-ip", client_ip or "",
        "--dst-ip", dst_ip or "",
        "--dpt", str(dst_port),
        "--max-age", str(max_age_sec)
    ]
    res = run_core_command(args)
    if isinstance(res, dict) and res.get("email"):
        return res.get("email"), res.get("ip") or client_ip, res.get("inbound_tag")
    return None, None, None


def find_hysteria_client_email(
    lines: List[str],
    dst_ip: Optional[str],
    dst_port: int,
    max_age_sec: int = 300
) -> Optional[str]:
    """Searches Hysteria 2 log lines for client user/email via sentinel-core."""
    lines_json = json.dumps(lines)
    if get_sentinel_lib():
        try:
            email = _ffi_call_str("SentinelFindHysteriaClientEmail", lines_json, dst_ip or "", int(dst_port), int(max_age_sec))
            if email:
                return email.strip()
            return None
        except Exception as e:
            logger.debug("FFI find_hysteria_client_email error: %s", e)
            return None

    if len(lines_json) > 32768:
        return None

    args = [
        "security", "find-proxy-client",
        "--core", "hysteria",
        "--lines", lines_json,
        "--dst-ip", dst_ip or "",
        "--dpt", str(dst_port),
        "--max-age", str(max_age_sec)
    ]
    res = run_core_command(args)
    if isinstance(res, dict) and res.get("email"):
        return res["email"].strip()
    return None


def find_client_ip_for_email_in_hysteria_log(
    lines: List[str],
    email: str,
    max_age_sec: int = 300
) -> Optional[str]:
    """Searches Hysteria 2 log lines for latest client IP by email via sentinel-core."""
    lines_json = json.dumps(lines)
    if get_sentinel_lib():
        try:
            ip = _ffi_call_str("SentinelFindClientIPForEmail", lines_json, email, int(max_age_sec))
            if ip:
                return ip.strip()
            return None
        except Exception as e:
            logger.debug("FFI find_client_ip_for_email_in_hysteria_log error: %s", e)
            return None

    if len(lines_json) > 32768:
        return None

    args = [
        "security", "find-proxy-client",
        "--core", "hysteria-ip",
        "--lines", lines_json,
        "--email", email,
        "--max-age", str(max_age_sec)
    ]
    res = run_core_command(args)
    if isinstance(res, dict) and res.get("client_ip"):
        return res["client_ip"].strip()
    return None


def parse_auth_line(line: str) -> Optional[Dict[str, Any]]:
    """Parses auth log lines (SSH, sudo, PVE Web GUI) via sentinel-core."""
    try:
        res = _ffi_call_json("SentinelParseAuthLogLine", line)
        if isinstance(res, dict) and "type" in res:
            return res
    except Exception as e:
        logger.debug("FFI parse_auth_line error: %s", e)

    res = run_core_command(["security", "parse-auth", "--line", line])
    if isinstance(res, dict) and "type" in res:
        return res
    return None


def parse_router_conntrack_line(line: str) -> Optional[Dict[str, Any]]:
    """Parses router conntrack line via sentinel-core."""
    try:
        res = _ffi_call_json("SentinelParseRouterConntrackLine", line)
        if isinstance(res, dict) and "src_ip" in res:
            return res
    except Exception as e:
        logger.debug("FFI parse_router_conntrack_line error: %s", e)

    res = run_core_command(["security", "parse-router", "--line", line])
    if isinstance(res, dict) and "src_ip" in res:
        return res
    return None


def parse_router_iptables_line(line: str) -> Optional[Dict[str, Any]]:
    """Parses router iptables syslog line via sentinel-core."""
    try:
        res = _ffi_call_json("SentinelParseRouterIptablesLine", line)
        if isinstance(res, dict) and "src_ip" in res:
            return res
    except Exception as e:
        logger.debug("FFI parse_router_iptables_line error: %s", e)

    res = run_core_command(["security", "parse-router", "--line", line])
    if isinstance(res, dict) and "src_ip" in res:
        return res
    return None


def ping_host(host: str, port: int = 443, timeout_ms: int = 3000) -> Dict[str, Any]:
    """Performs TCP latency handshake via sentinel-core."""
    try:
        res = _ffi_call_json("SentinelPing", host, int(port), int(timeout_ms))
        if isinstance(res, dict) and "success" in res:
            return res
    except Exception as e:
        logger.debug("FFI ping_host error: %s", e)

    res = run_core_command(["ping", host, "--port", str(port), "--timeout-ms", str(timeout_ms)])
    if isinstance(res, dict):
        return res
    return {"success": False, "error": "failed to ping"}


def parse_subscription(content: str) -> List[Dict[str, Any]]:
    """Parses multi-line or base64 subscription into a list of normalized ServerProfiles."""
    if not content or not content.strip():
        return []

    try:
        res = _ffi_call_json("SentinelParseSubscription", content)
        if isinstance(res, list):
            return res
    except Exception as e:
        logger.debug("FFI SentinelParseSubscription error: %s", e)

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_name = f.name

    try:
        res = run_core_command(["parse-subscription", "--file", tmp_name])
        if isinstance(res, list):
            return res
    finally:
        try:
            os.remove(tmp_name)
        except Exception:
            pass
    return []


def check_proxies(
    proxies: List[str],
    target_host: str = "api.telegram.org",
    target_port: int = 443,
    use_tls: bool = True,
    timeout_ms: int = 3000,
    concurrency: int = 64
) -> List[Dict[str, Any]]:
    """Checks batch of proxies / VLESS links concurrently with high performance in sentinel-core."""
    if not proxies:
        return []

    proxies_json = json.dumps(proxies)
    try:
        res = _ffi_call_json(
            "SentinelBatchCheckProxies",
            proxies_json,
            target_host,
            int(target_port),
            1 if use_tls else 0,
            int(timeout_ms),
            int(concurrency)
        )
        if isinstance(res, list):
            return res
    except Exception as e:
        logger.debug("FFI SentinelBatchCheckProxies error: %s", e)

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(proxies))
        tmp_name = f.name

    try:
        args = [
            "check-proxies",
            "--file", tmp_name,
            "--target", target_host,
            "--port", str(target_port),
            "--timeout-ms", str(timeout_ms),
            "--concurrency", str(concurrency)
        ]
        if not use_tls:
            args.append("--tls=false")
        res = run_core_command(args)
        if isinstance(res, list):
            return res
    finally:
        try:
            os.remove(tmp_name)
        except Exception:
            pass
    return []


def find_fastest_proxy(
    proxies: List[str],
    target_host: str = "api.telegram.org",
    target_port: int = 443,
    use_tls: bool = True,
    timeout_ms: int = 3000,
    concurrency: int = 64
) -> Optional[Dict[str, Any]]:
    """Finds fastest responsive proxy / VLESS link using sentinel-core batch probing."""
    if not proxies:
        return None

    proxies_json = json.dumps(proxies)
    try:
        res = _ffi_call_json(
            "SentinelFindFastestProxy",
            proxies_json,
            target_host,
            int(target_port),
            1 if use_tls else 0,
            int(timeout_ms),
            int(concurrency)
        )
        if isinstance(res, dict) and res.get("success"):
            return res
    except Exception as e:
        logger.debug("FFI SentinelFindFastestProxy error: %s", e)

    all_res = check_proxies(proxies, target_host, target_port, use_tls, timeout_ms, concurrency)
    working = [r for r in all_res if r.get("success")]
    if working:
        working.sort(key=lambda x: x.get("latencyMs", 99999))
        return working[0]
    return None


def build_failover_client_config(
    profiles: List[Dict[str, Any]],
    socks_port: int = 10808,
    http_port: int = 10809,
    health_url: str = "https://api.telegram.org"
) -> Optional[str]:
    """Generates complete Sing-box client JSON config with SOCKS5/HTTP inbound and multi-node failover."""
    if not profiles:
        return None

    profiles_json = json.dumps(profiles)
    try:
        res = _ffi_call_json(
            "SentinelBuildFailoverClientConfig",
            profiles_json,
            "singbox",
            int(socks_port),
            int(http_port),
            health_url
        )
        if isinstance(res, dict) and res.get("configJson"):
            return res["configJson"]
    except Exception as e:
        logger.debug("FFI SentinelBuildFailoverClientConfig error: %s", e)

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(profiles_json)
        tmp_name = f.name

    try:
        args = [
            "build-failover",
            "--file", tmp_name,
            "--core", "singbox",
            "--socks", str(socks_port),
            "--http", str(http_port),
            "--url", health_url
        ]
        res = run_core_command(args, parse_json=False)
        if res and isinstance(res, str) and ("inbounds" in res or "outbounds" in res):
            return res
    finally:
        try:
            os.remove(tmp_name)
        except Exception:
            pass
    return None


def set_core_language(lang: str) -> bool:
    """Sets language locale in Go sentinel-core ('ru' or 'en')."""
    try:
        res = _ffi_call_json("SentinelSetLanguage", lang)
        return isinstance(res, dict) and res.get("success") is True
    except Exception:
        return False


