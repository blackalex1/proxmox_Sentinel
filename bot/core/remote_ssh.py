import asyncio
import logging
import shlex
import asyncssh

from core.runtime_state import recent_bot_ports

# Хранилище постоянных соединений: server_ip -> asyncssh.SSHClientConnection
_ssh_connections = {}
_conn_lock = asyncio.Lock()


def get_ssh_base_cmd(server):
    """Возвращает базовый массив аргументов для подключения по SSH к конкретному VPS."""
    return [
        "ssh",
        "-i", server['key'],
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        f"{server['user']}@{server['ip']}"
    ]


async def get_ssh_connection(server) -> asyncssh.SSHClientConnection:
    """Возвращает активное закэшированное асинхронное соединение asyncssh, либо создает новое."""
    ip = server['ip']
    async with _conn_lock:
        conn = _ssh_connections.get(ip)
        if conn is None or conn.is_closed():
            logging.info("remote_ssh_establishing_new_asyncssh_connection", ip)
            try:
                conn = await asyncssh.connect(
                    ip,
                    username=server['user'],
                    client_keys=[server['key']],
                    known_hosts=None,
                    connect_timeout=10,
                    keepalive_interval=30,
                    keepalive_count_max=3
                )

                try:
                    sock = conn.get_extra_info('socket')
                    if sock:
                        sockname = sock.getsockname()
                        recent_bot_ports.append(sockname[1])
                except Exception:
                    pass

                _ssh_connections[ip] = conn
                logging.info("remote_ssh_async_connection_successfully_established_and", ip)
            except Exception as e:
                logging.error("remote_ssh_connection_error", ip, e)
                raise e
        return conn


async def run_remote_ssh_cmd(server, command_args):
    """Выполняет команду на удаленном сервере VPS через закэшированный асинхронный туннель asyncssh."""
    ip = server['ip']
    if isinstance(command_args, (list, tuple)):
        cmd_str = command_args[0] if len(command_args) == 1 else shlex.join(command_args)
    else:
        cmd_str = str(command_args)
    try:
        conn = await get_ssh_connection(server)
        result = await conn.run(cmd_str, check=False)
        return result.exit_status == 0, result.stdout.strip(), result.stderr.strip()
    except (asyncssh.Error, OSError, ConnectionError, asyncio.TimeoutError) as e:
        logging.warning("remote_ssh_connection_error_retrying_reconnection", ip, e)
        async with _conn_lock:
            if ip in _ssh_connections:
                try:
                    _ssh_connections[ip].close()
                except Exception:
                    pass
                del _ssh_connections[ip]
        try:
            conn = await get_ssh_connection(server)
            result = await conn.run(cmd_str, check=False)
            return result.exit_status == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e_retry:
            logging.error("remote_ssh_retry_failed_with_error", ip, e_retry)
            return False, "", str(e_retry)
    except Exception as e:
        logging.error("remote_ssh_critical_error_executing_command", ip, e)
        return False, "", str(e)
