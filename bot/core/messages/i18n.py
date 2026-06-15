import importlib
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class Translator:
    def __init__(self, lang: str = "ru"):
        self.lang = lang.lower()
        self.cache = {}

    def get(self, namespace: str, key: str, default: str = None, **kwargs) -> str:
        cache_key = f"{self.lang}.{namespace}"
        if cache_key not in self.cache:
            try:
                module = importlib.import_module(f"core.messages.locales.{self.lang}.{namespace}")
                self.cache[cache_key] = getattr(module, "translation", {})
            except ModuleNotFoundError as e:
                logger.debug(f"Locale module for {self.lang}.{namespace} not found: {e}")
                self.cache[cache_key] = {}
        
        val = self.cache[cache_key].get(key)
        if val is None:
            # Fallback to English if current lang is not English
            if self.lang != "en":
                fb_cache_key = f"en.{namespace}"
                if fb_cache_key not in self.cache:
                    try:
                        module = importlib.import_module(f"core.messages.locales.en.{namespace}")
                        self.cache[fb_cache_key] = getattr(module, "translation", {})
                    except ModuleNotFoundError:
                        self.cache[fb_cache_key] = {}
                val = self.cache[fb_cache_key].get(key)
            
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
translator = Translator(settings.bot_language)

def _(namespace: str, key: str, default: str = None, **kwargs) -> str:
    return translator.get(namespace, key, default, **kwargs)
