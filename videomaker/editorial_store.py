"""Durable per-scan editorial checkpoints, independent of browser/server sessions."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from pathlib import Path


class EditorialStore:
    TEXT_FIELDS = ('raw_script', 'prepared_script', 'source_text', 'curated', 'cleaned')

    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.RLock()

    @staticmethod
    def key_for(source):
        origin = source.get('_editorial_origin') or source
        identity = {key: origin.get(key) for key in ('json', 'url', 'content', 'post', 'comments', 'images')}
        return hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:32]

    def path_for(self, key):
        if not re.fullmatch(r'[a-f0-9]{32}', str(key)):
            raise ValueError('Mã phiên biên tập không hợp lệ.')
        return self.root / (key + '.json')

    def save(self, source, draft):
        selected = {}
        for field in self.TEXT_FIELDS:
            value = draft.get(field, '')
            if not isinstance(value, str) or len(value) > 500_000:
                raise ValueError('Bản thảo không hợp lệ hoặc quá dài: ' + field)
            selected[field] = value
        stage = draft.get('stage', 0)
        if isinstance(stage, bool) or not isinstance(stage, int) or not 0 <= stage <= 3:
            raise ValueError('Bước biên tập cần từ 0 đến 3.')
        selected.update(stage=stage, check_images=bool(draft.get('check_images', True)),
                        report=draft.get('report') if isinstance(draft.get('report'), dict) else None)
        revision = draft.get('client_revision', 0)
        if isinstance(revision, bool) or not isinstance(revision, (int, float)) or revision < 0:
            raise ValueError('Phiên bản bản thảo không hợp lệ.')
        selected['client_revision'] = revision
        key = self.key_for(source)
        origin = source.get('_editorial_origin') or source
        data = {'version': 1, 'id': key, 'updated': time.time(), 'content': source.get('content') or '',
                'source_path': origin.get('json') or '', 'source': source, 'draft': selected}
        encoded = json.dumps(data, ensure_ascii=False, indent=2)
        if len(encoded.encode('utf-8')) > 12_000_000:
            raise ValueError('Phiên biên tập quá lớn để lưu.')
        with self.lock:
            self.root.mkdir(parents=True, exist_ok=True)
            target = self.path_for(key)
            if target.exists() and revision:
                previous = self.load(key)
                if previous['draft'].get('client_revision', 0) > revision:
                    return {'id': key, 'updated': previous['updated'], 'stale': True}
            temporary = target.with_suffix('.tmp')
            temporary.write_text(encoded, encoding='utf-8')
            temporary.replace(target)
        return {'id': key, 'updated': data['updated']}

    def load(self, key):
        with self.lock:
            try:
                data = json.loads(self.path_for(key).read_text(encoding='utf-8'))
            except FileNotFoundError as error:
                raise ValueError('Không tìm thấy phiên biên tập đã lưu.') from error
        if data.get('version') != 1 or not isinstance(data.get('source'), dict) or not isinstance(data.get('draft'), dict):
            raise ValueError('File phiên biên tập không đúng định dạng.')
        return data

    def list_items(self):
        items = []
        with self.lock:
            for path in self.root.glob('*.json'):
                try:
                    data = self.load(path.stem)
                except (ValueError, OSError):
                    continue
                draft = data['draft']
                items.append({'id': data['id'], 'kind': 'workspace', 'label': data.get('content') or (data['source'].get('post') or {}).get('handle') or 'Bài Threads',
                              'updated': data.get('updated') or path.stat().st_mtime, 'stage': draft.get('stage', 0),
                              'source_path': data.get('source_path') or '',
                              'has_curated': bool(draft.get('curated')), 'has_cleaned': bool(draft.get('cleaned'))})
        return sorted(items, key=lambda item: item['updated'], reverse=True)


class ThreadsScriptStore(EditorialStore):
    """Keep raw and edited video scripts together, separately from editorial stages."""
    TEXT_FIELDS = ('raw_script', 'edited_script')
