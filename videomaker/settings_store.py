"""Persist application settings separately from the user's current video draft."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

DRAFT_KEYS = frozenset({'script', 'content'})
_LOCK = threading.RLock()


def draft_path(settings_file: Path) -> Path:
    return settings_file.parent.parent / 'work' / 'video-draft.json'


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


def load_state(settings_file: Path) -> tuple[dict, dict]:
    """Move legacy draft keys only after safely saving the draft; never replace an existing draft."""
    with _LOCK:
        settings = _read(settings_file)
        destination = draft_path(settings_file)
        draft = _read(destination)
        if DRAFT_KEYS.intersection(settings):
            if not destination.exists():
                draft = {key: settings.get(key, '') for key in DRAFT_KEYS}
                _write(destination, draft)
            settings = {key: value for key, value in settings.items() if key not in DRAFT_KEYS}
            _write(settings_file, settings)
        return settings, {key: draft.get(key, '') for key in DRAFT_KEYS}


def save_state(settings_file: Path, settings: dict, draft_updates: dict) -> None:
    with _LOCK:
        _, draft = load_state(settings_file)
        if draft_updates:
            draft.update({key: value for key, value in draft_updates.items() if key in DRAFT_KEYS})
            _write(draft_path(settings_file), draft)
        _write(settings_file, {key: value for key, value in settings.items() if key not in DRAFT_KEYS})
