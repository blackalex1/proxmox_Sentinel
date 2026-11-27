import importlib
import logging
from core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_LOCALES = {"ru", "en"}

_NAMESPACE_TO_BUNDLE = {
    "ansible": "infra",
    "nodes": "infra",
    "proxmox": "infra",
    "resources": "infra",
    "auth": "security",
    "ban_center": "security",
    "threats": "security",
    "traffic": "security",
    "history": "ui",
    "keyboards": "ui",
    "proxy": "network",
    "router": "network",
    "whitelist": "network",
    "logs": "logs",
    "spectre": "spectre",
}

# Pre-registered static module dictionary to prevent dynamic import code injection
_STATIC_LOCALE_MODULES = {}


def _get_locale_dict(lang: str, namespace: str) -> dict:
    key = (lang, namespace)
    if key in _STATIC_LOCALE_MODULES:
        return _STATIC_LOCALE_MODULES[key]

    trans = {}
    bundle = _NAMESPACE_TO_BUNDLE.get(namespace)
    if lang in ALLOWED_LOCALES and bundle:
        try:
            mod = importlib.import_module(f"core.messages.locales.{lang}.{bundle}")
            if hasattr(mod, "translations"):
                trans = mod.translations.get(namespace, {})
            else:
                trans = getattr(mod, "translation", {})
        except Exception as e:
            logger.debug(f"Could not load locale {lang}.{namespace}: {e}")

    _STATIC_LOCALE_MODULES[key] = trans
    return trans

class Translator:
    def __init__(self, lang: str = "ru"):
        self._lang = self._normalize_lang(lang)
        self._cache = _STATIC_LOCALE_MODULES

    @staticmethod
    def _normalize_lang(lang: str) -> str:
        clean_lang = (lang or "ru").lower().strip()
        return clean_lang if clean_lang in ALLOWED_LOCALES else "ru"

    def get_lang(self) -> str:
        return self._lang

    def set_lang(self, lang: str) -> str:
        self._lang = self._normalize_lang(lang)
        return self._lang

    def clear_cache(self) -> None:
        self._cache.clear()

    def get(self, namespace: str, key: str, default: str = None, **kwargs) -> str:
        if not namespace or not namespace.isidentifier():
            return default if default is not None else f"{namespace}:{key}"
        
        trans_dict = _get_locale_dict(self._lang, namespace)
        val = trans_dict.get(key)
        if val is None and self._lang != "en":
            val = _get_locale_dict("en", namespace).get(key)
        
        if val is None:
            return default if default is not None else f"{namespace}:{key}"
            
        if kwargs:
            try:
                # Format string with keyword arguments
                return val.format(**kwargs)
            except Exception as e:
                logger.warning(f"Error formatting string for {namespace}:{key}: {e}")
                return val
        return val

# Instantiate global translator based on settings
translator = Translator(getattr(settings, "bot_language", "ru"))

def set_current_locale(lang: str):
    translator.set_lang(lang)

def get_current_locale() -> str:
    return translator.get_lang()

def _(namespace: str, key: str, default: str = None, **kwargs) -> str:
    return translator.get(namespace, key, default, **kwargs)
