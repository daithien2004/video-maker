import json
import tempfile
import unittest
from pathlib import Path

from videomaker.settings_store import load_state, save_state, draft_path


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.settings = Path(temporary.name) / 'config/settings.json'
        self.settings.parent.mkdir()

    def write_settings(self, value):
        self.settings.write_text(json.dumps(value), encoding='utf-8')

    def test_migrate_legacy_script_without_losing_settings(self):
        self.write_settings({'nvenc': True, 'speed': 1.15, 'script': 'Bản đang làm', 'content': 'demo'})
        settings, draft = load_state(self.settings)
        self.assertEqual(settings, {'nvenc': True, 'speed': 1.15})
        self.assertEqual(draft, {'script': 'Bản đang làm', 'content': 'demo'})
        self.assertEqual(json.loads(self.settings.read_text()), settings)
        self.assertEqual(json.loads(draft_path(self.settings).read_text(encoding='utf-8')), draft)

    def test_saving_preferences_does_not_replace_draft(self):
        self.write_settings({})
        save_state(self.settings, {'nvenc': True}, {'script': 'Keep', 'content': 'demo'})
        save_state(self.settings, {'nvenc': False, 'script': 'wrong'}, {})
        settings, draft = load_state(self.settings)
        self.assertEqual(settings, {'nvenc': False})
        self.assertEqual(draft['script'], 'Keep')

    def test_existing_draft_wins_over_legacy_defaults(self):
        self.write_settings({'script': 'old sample', 'content': 'sample', 'nvenc': True})
        path = draft_path(self.settings)
        path.parent.mkdir()
        path.write_text('{"script": "current", "content": "mine"}')
        settings, draft = load_state(self.settings)
        self.assertEqual(draft, {'script': 'current', 'content': 'mine'})
        self.assertNotIn('script', settings)

    def test_corrupt_draft_does_not_delete_legacy_source(self):
        original = {'script': 'keep me', 'content': 'demo'}
        self.write_settings(original)
        path = draft_path(self.settings)
        path.parent.mkdir()
        path.write_text('broken')
        with self.assertRaises(ValueError):
            load_state(self.settings)
        self.assertEqual(json.loads(self.settings.read_text()), original)

    def test_migration_does_not_remove_source_if_draft_cannot_be_saved(self):
        from unittest.mock import patch
        self.write_settings({'script': 'keep me'})
        with patch('videomaker.settings_store._write', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                load_state(self.settings)
        self.assertEqual(json.loads(self.settings.read_text())['script'], 'keep me')
