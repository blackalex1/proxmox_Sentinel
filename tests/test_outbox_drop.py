import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import CallbackQuery
from core.outbox import ResilientOutbox

def test_drop_alerts_for_vmid():
    outbox = ResilientOutbox()
    outbox.queue = [
        {"chat_id": 123, "text": "🚨 Threat in LXC 102 (torserver)", "kwargs": {}},
        {"chat_id": 123, "text": "Proxmox Sentinel • Панель управления", "kwargs": {}},
        {"chat_id": 123, "text": "⚠️ Unusual port in LXC 102", "kwargs": {}},
        {"chat_id": 123, "text": "🚨 Threat in LXC 104 (Panel)", "kwargs": {}},
    ]
    dropped = outbox.drop_alerts_for_vmid(102)
    assert dropped == 2
    assert len(outbox.queue) == 2
    remaining_texts = [x["text"] for x in outbox.queue]
    assert "🚨 Threat in LXC 104 (Panel)" in remaining_texts
    assert "Proxmox Sentinel • Панель управления" in remaining_texts
