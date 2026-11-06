import datetime
import ipaddress
import logging
import os
import socket
import ssl
from typing import Tuple
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from core.config import settings, base_dir


DEFAULT_CERTS_DIR = os.path.join(base_dir, "config", "certs")
DEFAULT_CERT_PATH = os.path.join(DEFAULT_CERTS_DIR, "deck_api_cert.pem")
DEFAULT_KEY_PATH = os.path.join(DEFAULT_CERTS_DIR, "deck_api_key.pem")


def get_local_ip() -> str:
    """Определяет локальный IP-адрес машины в домашней сети"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ensure_self_signed_cert(
    cert_path: str = "",
    key_path: str = ""
) -> Tuple[str, str]:
    """
    Проверяет наличие SSL-сертификата и приватного ключа.
    Если пути не заданы или файлы отсутствуют — автоматически генерирует
    криптографически стойкий самоподписанный X.509 сертификат (RSA-2048, SHA-256)
    со сроком действия 10 лет и привязкой к локальным IP и хостам.
    """
    # 1. Если пути явно переданы из .env и файлы существуют — используем их
    if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    target_cert = cert_path or DEFAULT_CERT_PATH
    target_key = key_path or DEFAULT_KEY_PATH

    # 2. Если дефолтные файлы уже были созданы ранее — переиспользуем
    if os.path.exists(target_cert) and os.path.exists(target_key):
        return target_cert, target_key

    # 3. Автоматический выпуск нового самоподписанного сертификата
    os.makedirs(os.path.dirname(os.path.abspath(target_cert)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(target_key)), exist_ok=True)

    logging.info("[Deck API Security] Generating new 10-year self-signed TLS certificate & RSA key...")

    # Генерация RSA-2048 приватного ключа
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Формирование Subject и Issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Sentinel Ecosystem"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Sentinel Proxmox Security"),
        x509.NameAttribute(NameOID.COMMON_NAME, "SentinelDeckServer"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    local_ip = get_local_ip()

    # Сбор SAN (Subject Alternative Names) для поддержки подключения по IP и доменам
    san_list = [
        x509.DNSName("localhost"),
        x509.DNSName("sentinel.local"),
        x509.DNSName("proxmox.local"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address("0.0.0.0"))
    ]
    if local_ip not in ("127.0.0.1", "0.0.0.0"):
        try:
            san_list.append(x509.IPAddress(ipaddress.ip_address(local_ip)))
        except Exception:
            pass

    # Построение X.509 v3 сертификата
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))  # 10 лет
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Сохранение сертификата в PEM
    with open(target_cert, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Сохранение приватного ключа в PEM
    with open(target_key, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Установка прав доступа на чтение только владельцу на POSIX системах
    if os.name != 'nt':
        try:
            os.chmod(target_key, 0o600)
            os.chmod(target_cert, 0o644)
        except Exception:
            pass

    logging.info(f"✓ [Deck API Security] TLS Certificate saved: {target_cert}")
    logging.info(f"✓ [Deck API Security] TLS Private Key saved: {target_key}")

    return target_cert, target_key


def get_strict_ssl_context() -> ssl.SSLContext:
    """
    Создает строго HTTPS/WSS SSL-контекст.
    Если сертификата нет — автоматически выпускает самоподписанный.
    Откат к незашифрованному HTTP категорически запрещен.
    """
    configured_cert = getattr(settings, 'deck_api_ssl_cert', '').strip()
    configured_key = getattr(settings, 'deck_api_ssl_key', '').strip()

    cert_path, key_path = ensure_self_signed_cert(configured_cert, configured_key)

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        raise RuntimeError(
            f"[Deck API Security] Fatal: Cannot locate or generate SSL certificate: cert='{cert_path}', key='{key_path}'"
        )

    # Строгий TLS-серверный контекст (TLSv1.2 минимум, современные шифры)
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)

    return ssl_ctx
