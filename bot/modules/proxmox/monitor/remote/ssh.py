import asyncio
import logging

def get_ssh_base_cmd(server):
    """Возвращает базовый массив аргументов для подключения по SSH к конкретному VPS."""
    cmd = [
        "ssh",
        "-i", server['key'],
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        f"{server['user']}@{server['ip']}"
    ]
    return cmd

async def run_remote_ssh_cmd(server, command_args):
    """Выполняет команду на конкретном удаленном сервере через SSH."""
    try:
        ssh_base = get_ssh_base_cmd(server)
        cmd = ssh_base + command_args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return proc.returncode == 0, stdout_bytes.decode().strip(), stderr_bytes.decode().strip()
    except Exception as e:
        logging.error(f"[Remote SSH Exec {server['ip']}] Ошибка выполнения команды: {e}")
        return False, "", str(e)
