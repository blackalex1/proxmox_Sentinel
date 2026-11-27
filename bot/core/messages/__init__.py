# bot/core/messages/__init__.py
"""Узкий фасад локализации пакета сообщений."""

from .i18n import _, get_current_locale, set_current_locale, translator

__all__ = [
    "_",
    "translator",
    "get_current_locale",
    "set_current_locale",
]
