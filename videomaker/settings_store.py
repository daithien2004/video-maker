"""Persist video rendering settings."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

_LOCK = threading.RLock()

def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'Expected a JSON object: {path.name}')
    return value


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def load_settings(settings_file: Path) -> dict:
    with _LOCK:
        return _read(settings_file)


def save_settings(settings_file: Path, settings: dict) -> None:
    with _LOCK:
        _write(settings_file, settings)
