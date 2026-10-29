"""Durable checkpoints survive restart and cannot overwrite another scan or newer edits."""
import copy
import tempfile
import unittest
from pathlib import Path

from videomaker.editorial_store import EditorialStore


class EditorialStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'sessions'
        self.store = EditorialStore(self.directory)
        self.source = {'json': 'assets/illus/demo/post/threads.json', 'content': 'demo',
                       'url': 'https://threads.com/@a/post/1', 'post': {'id': 'ROOT', 'image': 'post/main.png', 'text': 'Bản gốc'},
                       'comments': [], 'images': [{'rel': 'post/main.png', 'path': 'assets/illus/demo/post/main.png'}]}
        self.draft = {'raw_script': 'Thô', 'prepared_script': 'Đã xếp', 'source_text': 'Cây nguồn',
                      'curated': 'Bản tuyển chọn', 'cleaned': 'Bản đọc', 'stage': 3, 'check_images': False,
                      'report': {'valid': True, 'status': 'passed', 'errors': [], 'warnings': [], 'counts': {}}}

    def test_restart_restores_all_fields_and_source_metadata(self):
        result = self.store.save(self.source, self.draft)
        restarted = EditorialStore(self.directory)
        restored = restarted.load(result['id'])
        self.assertEqual(restored['source'], self.source)
        for key, value in self.draft.items():
            self.assertEqual(restored['draft'][key], value)
        self.assertEqual(restarted.list_items()[0]['stage'], 3)

    def test_different_scan_in_same_folder_gets_separate_checkpoint(self):
        first = self.store.save(self.source, self.draft)
        next_scan = copy.deepcopy(self.source)
        next_scan['post']['id'] = 'DIFFERENT'
        second = self.store.save(next_scan, {**self.draft, 'curated': 'Bài khác'})
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(self.store.load(first['id'])['draft']['curated'], 'Bản tuyển chọn')
        self.assertEqual(len(self.store.list_items()), 2)

    def test_prepared_text_changes_keep_identity_of_original_scan(self):
        state = copy.deepcopy(self.source)
        state['_editorial_origin'] = copy.deepcopy(self.source)
        state['post']['text'] = 'Đã chỉnh bản thô'
        self.assertEqual(self.store.key_for(state), self.store.key_for(self.source))

    def test_late_save_cannot_replace_newer_pagehide_checkpoint(self):
        result = self.store.save(self.source, {**self.draft, 'curated': 'Mới nhất', 'client_revision': 20})
        stale = self.store.save(self.source, {**self.draft, 'curated': 'Đã cũ', 'client_revision': 10})
        self.assertTrue(stale['stale'])
        self.assertEqual(self.store.load(result['id'])['draft']['curated'], 'Mới nhất')

    def test_invalid_ids_and_steps_are_rejected(self):
        for key in ('../source', '', 'a' * 33):
            with self.assertRaises(ValueError):
                self.store.load(key)
        with self.assertRaises(ValueError):
            self.store.save(self.source, {**self.draft, 'stage': 100})

    def test_corrupt_file_does_not_hide_other_saved_scans(self):
        result = self.store.save(self.source, self.draft)
        (self.directory / ('f' * 32 + '.json')).write_text('broken', encoding='utf-8')
        self.assertEqual([item['id'] for item in self.store.list_items()], [result['id']])


if __name__ == '__main__':
    unittest.main()
