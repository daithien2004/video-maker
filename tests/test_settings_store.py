import tempfile
import unittest
from pathlib import Path

from videomaker.settings_store import load_settings, save_settings


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.settings = Path(temporary.name) / 'config/settings.json'

    def test_load_and_save_settings(self):
        expected = {'nvenc': True, 'speed': 1.15}
        save_settings(self.settings, expected)
        self.assertEqual(load_settings(self.settings), expected)

    def test_missing_settings_are_empty(self):
        self.assertEqual(load_settings(self.settings), {})

    def test_invalid_settings_raise_value_error(self):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text('broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_settings(self.settings)
