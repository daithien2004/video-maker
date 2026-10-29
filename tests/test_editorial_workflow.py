"""Manual editorial pipeline: source order, verbatim curation and validation reports."""
import copy
import unittest

from videomaker import threads_editorial as editorial


class EditorialWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.source = {'content': 'demo', 'url': 'https://www.threads.com/@author/post/demo',
            'post': {'id': 'ROOT', 'image': 'post/main.png', 'text': 'Bài gốc.', 'handle': 'author'},
            'comments': [
                {'id': 'R', 'parent_id': 'P', 'depth': 2, 'image': 'post/reply.png', 'text': 'Sao lại không?',
                 'handle': 'reply', 'datetime': '2026-10-28T02:01:00Z'},
                {'id': 'L', 'parent_id': 'ROOT', 'depth': 1, 'image': 'post/late.png', 'text': 'Một ý khác.',
                 'handle': 'late', 'datetime': '2026-10-28T03:00:00Z'},
                {'id': 'P', 'parent_id': 'ROOT', 'depth': 1, 'image': 'post/parent.png', 'text': 'Đúng rồi :)))',
                 'handle': 'parent', 'datetime': '2026-10-28T02:00:00Z'}], 'images': [], 'stats': {}}
        self.curated = '# post/main.png\nBài gốc. || -\n# post/parent.png\nĐúng rồi :))) || -\n# post/reply.png\nSao lại không? || -'
        self.cleaned = self.curated.replace('Đúng rồi :)))', 'Đúng rồi.')

    def report(self, curated=None, cleaned=None):
        return editorial.validate_workflow(self.source, self.curated if curated is None else curated,
                                           self.cleaned if cleaned is None else cleaned, require_images=False)

    def test_prepare_orders_parent_before_reply_without_rewriting_or_mutating(self):
        original = copy.deepcopy(self.source)
        result = editorial.prepare_workspace(self.source)
        self.assertEqual([item['image'] for item in result['tree']],
                         ['post/main.png', 'post/parent.png', 'post/reply.png', 'post/late.png'])
        self.assertEqual(result['tree'][2]['parent_image'], 'post/parent.png')
        self.assertIn('Đúng rồi :)))', result['source_text'])
        self.assertIn('Đúng rồi :))) || -', result['seed'])
        self.assertEqual(self.source, original)

    def test_valid_verbatim_curate_and_normalized_script_reports_counts(self):
        report = self.report()
        self.assertEqual(report['status'], 'passed')
        self.assertTrue(report['valid'])
        self.assertEqual(report['counts']['kept'], 2)
        self.assertEqual(report['counts']['dropped'], 1)
        self.assertEqual(report['dropped'][0]['image'], 'post/late.png')

    def test_curate_rewriting_is_an_error_with_stage_and_line(self):
        report = self.report(curated=self.curated.replace('Đúng rồi :)))', 'Tôi đồng ý'))
        error = next(issue for issue in report['errors'] if issue['code'] == 'changed_original')
        self.assertEqual(error['stage'], 'curated')
        self.assertEqual(error['line'], 3)
        self.assertFalse(report['valid'])

    def test_curate_allows_only_whitespace_splitting(self):
        curated = self.curated.replace('Bài gốc. || -', 'Bài || -\ngốc. || -').replace('Đúng rồi', 'Đúng  rồi')
        self.assertTrue(self.report(curated=curated)['valid'])

    def test_normalize_cannot_drop_or_reorder_selected_blocks(self):
        report = self.report(cleaned='# post/main.png\nBài gốc. || -')
        self.assertIn('changed_selection', [issue['code'] for issue in report['errors']])

    def test_validator_collects_leading_text_wrong_subtitle_and_missing_parent(self):
        invalid = 'Lời dẫn thêm.\n# post/main.png\nBài gốc. || CHỮ\n# post/reply.png\nSao lại không? || -'
        report = self.report(curated=invalid, cleaned=invalid)
        codes = {issue['code'] for issue in report['errors']}
        self.assertTrue({'missing_header', 'subtitle', 'parent_before_reply'} <= codes)

    def test_remaining_abbreviations_and_numbers_require_human_review(self):
        report = self.report(cleaned=self.cleaned.replace('Sao lại không?', 't sinh năm 2003'))
        self.assertTrue(report['valid'])
        self.assertEqual(report['status'], 'review')
        self.assertEqual({issue['code'] for issue in report['warnings']}, {'numbers', 'abbreviation'})

    def test_curate_keeps_prepared_chronological_group_order(self):
        curated = '# post/main.png\nBài gốc. || -\n# post/late.png\nMột ý khác. || -\n# post/parent.png\nĐúng rồi :))) || -'
        report = self.report(curated=curated, cleaned=curated)
        self.assertIn('source_order', [issue['code'] for issue in report['errors']])

    def test_empty_duplicate_and_unknown_blocks_are_reported(self):
        text = '# post/main.png\n# post/main.png\nBài gốc. || -\n# post/unknown.png\nLạ || -'
        report = self.report(curated=text, cleaned=text)
        self.assertTrue({'empty_section', 'duplicate_image', 'unknown_image'} <= {issue['code'] for issue in report['errors']})

    def test_file_check_can_be_enabled_without_a_render(self):
        report = editorial.validate_workflow(self.source, self.curated, self.cleaned, require_images=True)
        self.assertIn('missing_file', [issue['code'] for issue in report['errors']])

    def test_incomplete_context_is_flagged_and_empty_source_rejected(self):
        self.source['comments'][0]['parent_id'] = 'MISSING'
        prepared = editorial.prepare_workspace(self.source)
        self.assertTrue(prepared['warnings'])
        with self.assertRaises(ValueError):
            editorial.prepare_workspace({'post': {}})

    def test_prepare_uses_current_rough_script_and_retains_image_parent_metadata(self):
        original = copy.deepcopy(self.source)
        rough = self.curated.replace('Bài gốc.', 'Bản thô người dùng đang sửa.')
        snapshot = editorial.source_from_draft(self.source, rough)
        self.assertEqual(snapshot['post']['text'], 'Bản thô người dùng đang sửa.')
        self.assertEqual(snapshot['comments'][1]['parent_id'], 'P')
        self.assertTrue(editorial.validate_workflow(snapshot, rough, rough, require_images=False)['valid'])
        self.assertEqual(self.source, original)

    def test_rough_input_rejects_wrong_post_or_silently_dropped_leading_words(self):
        for rough in ('Ghi chú thành lời đọc\n' + self.curated,
                      self.curated.replace('post/main.png', 'post/another.png'),
                      '# post/parent.png\nĐúng rồi :))) || -'):
            with self.subTest(rough=rough), self.assertRaises(ValueError):
                editorial.source_from_draft(self.source, rough)


if __name__ == '__main__':
    unittest.main()
