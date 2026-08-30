import ast
import os
import sys
import glob
import pytest

# Add bot to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot'))
sys.path.insert(0, BASE_DIR)

def get_python_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        if "__pycache__" in root or ".venv" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files

def test_no_inline_multiline_html_in_handlers():
    """
    Scans all handler and monitor files to ensure no handler defines raw multi-line
    HTML alerts or tables inline instead of delegating to core.messages.
    """
    handler_files = get_python_files(os.path.join(BASE_DIR, "core", "handlers"))
    handler_files += get_python_files(os.path.join(BASE_DIR, "modules"))
    
    # Exclude core/messages, locales, test files, and sanitizer utils
    target_files = [
        f for f in handler_files 
        if "messages" not in f and "locales" not in f 
        and not f.endswith("outbox.py") 
        and not f.endswith("rich.py")
        and not (f.endswith("utils.py") and "monitor" in f)
    ]
    
    violations = []
    
    for file_path in target_files:
        rel_path = os.path.relpath(file_path, BASE_DIR)
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            
        try:
            tree = ast.parse(source, filename=file_path)
        except Exception as e:
            violations.append(f"{rel_path}: Failed to parse AST: {e}")
            continue
            
        for node in ast.walk(tree):
            # Check for multi-line string constants containing table tags or alert banners in handlers
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip()
                # If a handler embeds a <table> tag directly rather than in core/messages
                if "<table" in val:
                    violations.append(f"{rel_path}:{node.lineno} Found inline <table...> in handler/monitor: {val[:60]}...")
                    
                # If a handler embeds large multiline markdown alert banners with tables
                if ("### 🚨" in val and "\n" in val) or ("### 🛑" in val and "\n" in val) or ("### ⚠️" in val and "\n" in val):
                    violations.append(f"{rel_path}:{node.lineno} Found inline alert banner template in handler/monitor: {val[:60]}...")

    assert len(violations) == 0, "Found direct message formatting bypassing core.messages:\n" + "\n".join(violations)



def test_monitors_use_core_sender_and_messages():
    """
    Verifies that monitor modules import and use core.messages / core.sender.
    """
    monitor_dir = os.path.join(BASE_DIR, "modules", "proxmox", "monitor")
    if not os.path.exists(monitor_dir):
        return
        
    monitor_files = get_python_files(monitor_dir)
    for file_path in monitor_files:
        rel_path = os.path.relpath(file_path, BASE_DIR)
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            
        tree = ast.parse(source, filename=file_path)
        
        # Check that no monitor directly calls bot.send_message bypassing sender/messages
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "send_message":
                    # Check if caller is 'bot'
                    if isinstance(func.value, ast.Name) and func.value.id == "bot":
                        # Verify if this file is sender.py or monitor utils wrapping it
                        if not rel_path.endswith("sender.py") and not rel_path.endswith("outbox.py"):
                            pytest.fail(f"{rel_path}:{node.lineno} Direct call to bot.send_message found in monitor. Must use send_alert_to_admins or send_rich_message from core.sender.")

