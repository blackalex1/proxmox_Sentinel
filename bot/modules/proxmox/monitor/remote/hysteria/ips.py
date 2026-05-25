import logging
from ..ssh import run_remote_ssh_cmd

async def block_remote_hysteria_user(server, username):
    """Блокирует пользователя Hysteria на конкретном удаленном VPS через MongoDB и сбрасывает сессию."""
    eval_str = f"db.users.updateOne({{_id: '{username}'}}, {{\\$set: {{blocked: true}}}})"
    db_cmd = [f"mongosh blitz_panel --quiet --eval \"{eval_str}\""]
    success, stdout, stderr = await run_remote_ssh_cmd(server, db_cmd)
    if success:
        logging.info(f"[Hysteria IPS {server['ip']}] Пользователь {username} успешно заблокирован в MongoDB.")
        
        kick_script = (
            'import json, urllib.request; '
            'cfg = json.load(open("/etc/hysteria/config.json")); '
            'ts = cfg.get("trafficStats", {}); '
            'secret = ts.get("secret", ""); '
            'port = ts.get("listen", "").split(":")[-1]; '
            'req = urllib.request.Request(f"http://127.0.0.1:{port}/kick", '
            f'data=json.dumps(["{username}"]).encode(), '
            'headers={"Authorization": secret, "Content-Type": "application/json"}, method="POST"); '
            'urllib.request.urlopen(req)'
        )
        kick_cmd = [f"python3 -c '{kick_script}'"]
        kick_success, _, kick_err = await run_remote_ssh_cmd(server, kick_cmd)
        if kick_success:
            logging.info(f"[Hysteria IPS {server['ip']}] Активные сессии пользователя {username} успешно сброшены.")
        else:
            logging.warning(f"[Hysteria IPS {server['ip']}] Не удалось сбросить активные сессии {username}: {kick_err}")
    else:
        logging.error(f"[Hysteria IPS {server['ip']}] Не удалось заблокировать {username} на VPS: {stderr}")
    return success

async def unblock_remote_hysteria_user(server, username):
    """Разблокирует пользователя Hysteria на конкретном удаленном VPS через MongoDB."""
    if not server:
        logging.error(f"[Hysteria IPS] Разблокировка невозможна: сервер не передан.")
        return False
        
    eval_str = f"db.users.updateOne({{_id: '{username}'}}, {{\\$set: {{blocked: false}}}})"
    cmd = [f"mongosh blitz_panel --quiet --eval \"{eval_str}\""]
    success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
    if success:
        logging.info(f"[Hysteria IPS {server['ip']}] Пользователь {username} успешно разблокирован в MongoDB.")
    else:
        logging.error(f"[Hysteria IPS {server['ip']}] Не удалось разблокировать {username}: {stderr}")
    return success
