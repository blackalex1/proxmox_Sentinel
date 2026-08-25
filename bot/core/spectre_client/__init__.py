from .client import SpectrePanelInstance, parse_env_content, probe_panel_url, normalize_url
from .manager import SpectreClientManager, spectre_manager

# Sentinel Panel Aliases
SentinelPanelInstance = SpectrePanelInstance
SentinelPanelManager = SpectreClientManager
sentinel_manager = spectre_manager

__all__ = [
    "SpectrePanelInstance",
    "SentinelPanelInstance",
    "parse_env_content",
    "probe_panel_url",
    "normalize_url",
    "SpectreClientManager",
    "SentinelPanelManager",
    "spectre_manager",
    "sentinel_manager",
]
