"""Modular Installer and Updater for Sentinel Controller."""

from .common import run_command, log_info, log_success, log_warn, log_error, log_banner
from .downloader import Downloader
from .git import GitManager
from .network import NetworkManager
from .core import CoreManager
from .engines import ProxyEngineManager
from .dependencies import DependencyManager
from .service import ServiceManager

__version__ = "1.0.0"
__all__ = [
    "Downloader",
    "GitManager",
    "NetworkManager",
    "CoreManager",
    "ProxyEngineManager",
    "DependencyManager",
    "ServiceManager",
]
