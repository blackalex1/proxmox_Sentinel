import logging
from core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_LOCALES = {"ru", "en"}

# Pre-registered static module dictionary to prevent dynamic import code injection
_STATIC_LOCALE_MODULES = {}

def _get_locale_dict(lang: str, namespace: str) -> dict:
    key = (lang, namespace)
    if key in _STATIC_LOCALE_MODULES:
        return _STATIC_LOCALE_MODULES[key]
    
    # Safe static loader
    mod = None
    try:
        if lang == "ru":
            if namespace == "ansible": from core.messages.locales.ru import ansible as mod
            elif namespace == "auth": from core.messages.locales.ru import auth as mod
            elif namespace == "ban_center": from core.messages.locales.ru import ban_center as mod
            elif namespace == "history": from core.messages.locales.ru import history as mod
            elif namespace == "keyboards": from core.messages.locales.ru import keyboards as mod
            elif namespace == "logs": from core.messages.locales.ru import logs as mod
            elif namespace == "nodes": from core.messages.locales.ru import nodes as mod
            elif namespace == "proxmox": from core.messages.locales.ru import proxmox as mod
            elif namespace == "proxy": from core.messages.locales.ru import proxy as mod
            elif namespace == "resources": from core.messages.locales.ru import resources as mod
            elif namespace == "router": from core.messages.locales.ru import router as mod
            elif namespace == "spectre": from core.messages.locales.ru import spectre as mod
            elif namespace == "threats": from core.messages.locales.ru import threats as mod
            elif namespace == "traffic": from core.messages.locales.ru import traffic as mod
            elif namespace == "whitelist": from core.messages.locales.ru import whitelist as mod
        elif lang == "en":
            if namespace == "ansible": from core.messages.locales.en import ansible as mod
            elif namespace == "auth": from core.messages.locales.en import auth as mod
            elif namespace == "ban_center": from core.messages.locales.en import ban_center as mod
            elif namespace == "history": from core.messages.locales.en import history as mod
            elif namespace == "keyboards": from core.messages.locales.en import keyboards as mod
            elif namespace == "logs": from core.messages.locales.en import logs as mod
            elif namespace == "nodes": from core.messages.locales.en import nodes as mod
            elif namespace == "proxmox": from core.messages.locales.en import proxmox as mod
            elif namespace == "proxy": from core.messages.locales.en import proxy as mod
            elif namespace == "resources": from core.messages.locales.en import resources as mod
            elif namespace == "router": from core.messages.locales.en import router as mod
            elif namespace == "spectre": from core.messages.locales.en import spectre as mod
            elif namespace == "threats": from core.messages.locales.en import threats as mod
            elif namespace == "traffic": from core.messages.locales.en import traffic as mod
            elif namespace == "whitelist": from core.messages.locales.en import whitelist as mod
    except Exception as e:
        logger.debug(f"Could not load locale {lang}.{namespace}: {e}")

    trans = getattr(mod, "translation", {}) if mod else {}
    _STATIC_LOCALE_MODULES[key] = trans
    return trans

class Translator:
    def __init__(self, lang: str = "ru"):
        clean_lang = (lang or "ru").lower().strip()
        self.lang = clean_lang if clean_lang in ALLOWED_LOCALES else "ru"
        self.cache = _STATIC_LOCALE_MODULES

    def get(self, namespace: str, key: str, default: str = None, **kwargs) -> str:
        if not namespace or not namespace.isidentifier():
            return default if default is not None else f"{namespace}:{key}"
        
        trans_dict = _get_locale_dict(self.lang, namespace)
        val = trans_dict.get(key)
        if val is None and self.lang != "en":
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
    global translator
    translator = Translator(lang)

def get_current_locale() -> str:
    return translator.lang

def _(namespace: str, key: str, default: str = None, **kwargs) -> str:
    return translator.get(namespace, key, default, **kwargs)
