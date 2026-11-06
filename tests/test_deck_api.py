import asyncio
import json
import os
import ssl
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from cryptography import x509

from core.config import settings
from modules.deck_api.auth import verify_bearer_token, SlidingWindowRateLimiter, extract_token_from_request
from modules.deck_api.broadcaster import deck_broadcaster, sanitize_text
from modules.deck_api.server import create_deck_api_app, start_deck_api_server
from modules.deck_api.crypto import ensure_self_signed_cert, get_strict_ssl_context
from modules.deck_api.routes import setup_routes


class TestDeckApiSecurity(AioHTTPTestCase):
    VALID_TOKEN = "a" * 32  # 32-символьный токен для безопасного тестирования

    async def get_application(self):
        settings.deck_api_token = self.VALID_TOKEN
        settings.enable_deck_api = True
        return create_deck_api_app()

    async def test_bearer_token_verification_logic(self):
        """Проверка безопасного сравнения токенов (timing-attack safe)"""
        assert verify_bearer_token(self.VALID_TOKEN, self.VALID_TOKEN) is True
        assert verify_bearer_token("wrong_token_1234567890", self.VALID_TOKEN) is False
        assert verify_bearer_token("", self.VALID_TOKEN) is False
        assert verify_bearer_token(self.VALID_TOKEN, "") is False

    async def test_health_endpoint_unauthorized(self):
        """Без Bearer-токена эндпоинт должен возвращать HTTP 401 Unauthorized"""
        resp = await self.client.get("/api/v1/health")
        assert resp.status == 401
        data = await resp.json()
        assert data.get("error") == "Unauthorized"
        assert "WWW-Authenticate" in resp.headers

    async def test_health_endpoint_invalid_token(self):
        """С невалидным Bearer-токеном эндпоинт должен возвращать 401"""
        headers = {"Authorization": "Bearer invalid_secret_token_12345"}
        resp = await self.client.get("/api/v1/health", headers=headers)
        assert resp.status == 401

    async def test_health_endpoint_authorized(self):
        """С валидным Bearer-токеном эндпоинт должен отдавать 200 и статус ok"""
        headers = {"Authorization": f"Bearer {self.VALID_TOKEN}"}
        resp = await self.client.get("/api/v1/health", headers=headers)
        assert resp.status == 200
        data = await resp.json()
        assert data.get("status") == "ok"
        # Проверка внедрения защитных заголовков (Secure Headers)
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"

    async def test_alerts_endpoint(self):
        """Проверка получения списка алертов через защищенный REST API"""
        await deck_broadcaster.broadcast_alert("Тестовый алерт вторжения", severity="CRITICAL")
        
        headers = {"Authorization": f"Bearer {self.VALID_TOKEN}"}
        resp = await self.client.get("/api/v1/alerts", headers=headers)
        assert resp.status == 200
        data = await resp.json()
        assert "alerts" in data
        assert len(data["alerts"]) > 0
        assert data["alerts"][-1]["text"] == "Тестовый алерт вторжения"
        assert data["alerts"][-1]["severity"] == "CRITICAL"

    async def test_websocket_stream_and_broadcasting(self):
        """Тестирование подключения по WebSocket, пинга и получения broadcast алертов"""
        headers = {"Authorization": f"Bearer {self.VALID_TOKEN}"}
        ws = await self.client.ws_connect("/api/v1/ws/stream", headers=headers)

        # 1. Проверяем получение initial snapshot
        init_msg = await ws.receive_json(timeout=5.0)
        assert init_msg.get("type") == "init"
        assert "recent_alerts" in init_msg

        # 2. Проверяем интерактивный пинг-понг
        await ws.send_json({"action": "ping"})
        pong_msg = await ws.receive_json(timeout=5.0)
        assert pong_msg.get("type") == "pong"

        # 3. Проверяем вещание алерта через брокер
        await deck_broadcaster.broadcast_alert("⚠️ ВНИМАНИЕ: Падение ноды pve-node1!")
        alert_msg = await ws.receive_json(timeout=5.0)
        assert alert_msg.get("type") == "alert"
        assert "Падение ноды pve-node1" in alert_msg.get("text")
        assert alert_msg.get("severity") == "CRITICAL"

        await ws.close()
        await asyncio.sleep(0.05)

    def test_text_sanitization(self):
        """Проверка маскирования паролей, токенов и очистки ANSI кодов"""
        ansi_text = "\x1b[31;1mCRITICAL ALERT\x1b[0m: Connection refused"
        assert sanitize_text(ansi_text) == "CRITICAL ALERT: Connection refused"

        secret_text = "Login with password=SuperSecretPassword! and Bearer my_super_secret_token_abcdef12345"
        sanitized = sanitize_text(secret_text)
        assert "SuperSecretPassword" not in sanitized
        assert "[REDACTED_PASSWORD]" in sanitized
        assert "my_super_secret_token" not in sanitized
        assert "[REDACTED_TOKEN]" in sanitized

    def test_rate_limiter(self):
        """Тестирование Rate Limiter со скользящим окном"""
        limiter = SlidingWindowRateLimiter(limit=3, window_seconds=60)
        ip = "192.0.2.1"
        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is True
        # 4-й запрос превышает лимит в 3 запроса
        assert limiter.is_allowed(ip) is False

    async def test_conditional_server_startup(self):
        """Сервер НЕ должен запускаться, если enable_deck_api=False"""
        with patch.object(settings, 'enable_deck_api', False):
            await start_deck_api_server()
            assert deck_broadcaster.client_count == 0

    def test_self_signed_cert_auto_generation_and_ssl_context(self):
        """Проверка автоматической генерации самоподписанного TLS-сертификата и строгого контекста"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_cert = os.path.join(tmp_dir, "cert.pem")
            test_key = os.path.join(tmp_dir, "key.pem")

            # 1. Автоматический выпуск
            cert_out, key_out = ensure_self_signed_cert(test_cert, test_key)
            assert os.path.exists(cert_out)
            assert os.path.exists(key_out)

            # 2. Валидация свойств сертификата через cryptography
            with open(cert_out, "rb") as f:
                cert_obj = x509.load_pem_x509_certificate(f.read())
            
            # Срок действия ~10 лет
            days_valid = (cert_obj.not_valid_after_utc - cert_obj.not_valid_before_utc).days
            assert days_valid >= 3649

            # Subject CN
            common_name = cert_obj.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
            assert common_name == "SentinelDeckServer"

            # 3. Проверка создания строгого TLS SSL-контекста
            with patch.object(settings, 'deck_api_ssl_cert', cert_out), \
                 patch.object(settings, 'deck_api_ssl_key', key_out):
                ssl_ctx = get_strict_ssl_context()
                assert isinstance(ssl_ctx, ssl.SSLContext)
                assert ssl_ctx.minimum_version == ssl.TLSVersion.TLSv1_2
