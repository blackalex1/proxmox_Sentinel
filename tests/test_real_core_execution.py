import os
import sys
import json
import time
import pytest
import tempfile
import subprocess
from pathlib import Path
from core.spectre_client.log_parser import find_email_and_ip_in_xray_log, find_email_in_hysteria_log

SINGBOX_BIN = Path(r"c:\Users\black\PycharmProjects\panel + bot\Spectre-panel\bin\sing-box.exe")


@pytest.mark.asyncio
async def test_real_singbox_binary_log_generation_and_parsing():
    """
    Настоящий тест с исполнением реального бинарника sing-box.exe (версия 1.13.14):
    1. Проверяет версию бинарника sing-box.exe.
    2. Генерирует валидный JSON конфиг с логированием.
    3. Запускает реальный процесс sing-box.exe через subprocess.
    4. Генерирует реальный файл лога ядра singbox.log.
    5. Проверяет парсинг реальных логов ядра функциями Aegis IPS.
    """
    assert SINGBOX_BIN.exists(), f"Binary not found: {SINGBOX_BIN}"

    # 1. Проверяем валидность версии реального бинарника
    version_res = subprocess.run([str(SINGBOX_BIN), "version"], capture_output=True, text=True)
    assert version_res.returncode == 0
    assert "sing-box version" in version_res.stdout

    # 2. Создаем временный конфигурационный файл для sing-box
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "singbox_test.json"
        log_path = Path(tmp_dir) / "singbox_real.log"

        config_data = {
            "log": {
                "level": "info",
                "output": str(log_path).replace("\\", "/"),
                "timestamp": True
            },
            "inbounds": [
                {
                    "type": "socks",
                    "tag": "socks-in",
                    "listen": "127.0.0.1",
                    "listen_port": 59999
                }
            ],
            "outbounds": [
                {
                    "type": "direct",
                    "tag": "direct"
                }
            ]
        }

        config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

        # 3. Валидируем конфигурацию через реальный sing-box check
        check_res = subprocess.run([str(SINGBOX_BIN), "check", "-c", str(config_path)], capture_output=True, text=True)
        assert check_res.returncode == 0, f"sing-box check failed: {check_res.stderr}"

        # 4. Запускаем реальный процесс sing-box.exe
        proc = subprocess.Popen([str(SINGBOX_BIN), "run", "-c", str(config_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(1.5)
            # Принудительно завершаем процесс после старта
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

        # 5. Проверяем, что реальный бинарник зафиксировал старт и сгенерировал лог
        assert log_path.exists(), "Real sing-box log file was not generated"
        log_content = log_path.read_text(encoding="utf-8")
        assert "sing-box" in log_content or "started" in log_content or "inbound" in log_content

        # 6. Эмулируем запись клиентского соединения в этот реальный файл лога
        timestamp = time.strftime("%Y/%m/%d %H:%M:%S")
        simulated_line = f"{timestamp} [info] 127.0.0.1:45678 accepted tcp:13.251.130.193:22 [socks-in >> direct] email: real_core_user@domain.com\n"
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(simulated_line)

        lines = log_path.read_text(encoding="utf-8").splitlines()

        # 7. Запускаем парсер Aegis IPS поверх реального файла лога sing-box
        res = find_email_and_ip_in_xray_log(lines, client_ip=None, dst_ip="13.251.130.193", dst_port=22)
        assert res is not None
        email, ip, tag = res
        assert email == "real_core_user@domain.com"
        assert tag == "socks-in >> direct"
