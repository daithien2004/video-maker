"""Select comment/reply counts while keeping the order Threads displays."""
import unittest

from videomaker import threads_replies as tr, threads_options, threads_shot as ts


def comment(code, likes, hour, parent='ROOT'):
    return dict(id=code, handle=code, text='Text ' + code, likes=likes, replies=0,
                datetime=f'2026-10-28T{hour:02d}:00:00Z', parent_id=parent,
                url=f'https://www.threads.com/@user/post/{code}', image=f'post/{code}.png')


class ReplySelectionTests(unittest.TestCase):
    def setUp(self):
        self.post = comment('ROOT', 500, 0, None)

    def test_keeps_display_order_instead_of_ranking_by_likes_or_time(self):
        pool = [comment('FIRST', 1, 5), comment('SECOND', 100, 6),
                comment('R_LATE', 0, 9, 'FIRST'), comment('R_EARLY', 0, 4, 'FIRST'),
                comment('THIRD', 50, 10)]
        result = tr.select_conversations(pool, self.post, top=2, per_parent=2)
        # FIRST đứng đầu trang dù ít like nhất; THIRD nhiều like hơn nhưng bị cắt bởi top=2.
        self.assertEqual([item['id'] for item in result],
                         ['FIRST', 'R_LATE', 'R_EARLY', 'SECOND'])
        self.assertEqual([item['depth'] for item in result], [1, 2, 2, 1])
        limited = tr.select_conversations(pool, self.post, top=3, per_parent=1)
        self.assertEqual([item['id'] for item in limited], ['FIRST', 'R_LATE', 'SECOND', 'THIRD'])

    def test_existing_flattened_replies_count_toward_the_per_parent_limit(self):
        pool = [comment('P', 5, 1), comment('R1', 4, 2, 'P'), comment('R2', 2, 3, 'P'),
                comment('R3', 1, 4, 'P')]
        result = tr.select_conversations(pool, self.post, top=1, per_parent=2)
        self.assertEqual([item['id'] for item in result], ['P', 'R1', 'R2'])

    def test_reply_slots_can_be_filled_with_zero_likes(self):
        pool = [comment('P', 5, 1), comment('R1', 0, 2, 'P'), comment('R2', 0, 3, 'P')]
        result = tr.select_conversations(pool, self.post, top=1, per_parent=2)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(tr.select_conversations(pool, self.post, top=1, per_parent=0)), 1)

    def test_reply_does_not_consume_a_main_comment_slot(self):
        pool = [comment('REPLY', 100, 4, 'P1'), comment('P1', 10, 1), comment('P2', 8, 2), comment('P3', 1, 3)]
        result = tr.select_conversations(pool, self.post, top=2, per_parent=1)
        self.assertEqual([item['id'] for item in result], ['P1', 'REPLY', 'P2'])

    def test_collect_then_select_enforces_total_reply_count_on_flat_main_page(self):
        parent = comment('P', 10, 1)
        parent['replies'] = 3
        replies = [comment('R1', 0, 2), comment('R2', 0, 3), comment('R3', 0, 4)]
        result, stats = tr.collect([parent] + replies, self.post,
                                  lambda url: replies if url == parent['url'] else [],
                                  root_limit=1, per_parent=2, max_depth=1)
        self.assertEqual([item['id'] for item in result], ['P', 'R1', 'R2'])
        self.assertEqual(stats['selected_roots'], 1)
        self.assertEqual(stats['selected_replies'], 2)

    def test_nesting_depth_and_each_parent_count_are_respected(self):
        pool = [comment('P', 10, 1), comment('R', 5, 2, 'P'), comment('G', 0, 3, 'R')]
        result = tr.select_conversations(pool, self.post, top=1, per_parent=1, max_depth=1)
        self.assertEqual([item['id'] for item in result], ['P', 'R'])
        result = tr.select_conversations(pool, self.post, top=1, per_parent=1, max_depth=2)
        self.assertEqual([item['id'] for item in result], ['P', 'R', 'G'])

    def test_generated_script_keeps_the_scraped_order(self):
        pool = [comment('NEW', 100, 8), comment('CHILD', 0, 9, 'OLD'), comment('OLD', 50, 1)]
        result = tr.select_conversations(pool, self.post, top=2, per_parent=1)
        sections = ts.parse_sections(ts.build_editable_script({'post': self.post, 'comments': result}))
        self.assertEqual([image for image, _ in sections], ['post/ROOT.png', 'post/NEW.png', 'post/OLD.png', 'post/CHILD.png'])

    def test_main_comment_header_does_not_claim_it_replies_to_the_post(self):
        source = {'tag': 'post',
                  'post': {'id': 'ROOT', 'handle': 'root', 'text': 'Post', 'image': 'post/ROOT.png'},
                  'comments': [dict(comment('MAIN', 5, 1), depth=1, parent_handle='root'),
                               dict(comment('REPLY', 1, 2, 'MAIN'), depth=2, parent_handle='MAIN')]}
        headers = [line for line in ts.build_editable_script(source).splitlines()
                   if line.startswith('#')]
        self.assertNotIn('↳', headers[1])
        self.assertIn('↳ @MAIN', headers[2])

    def test_indented_reply_lands_under_its_parent_in_the_raw_script(self):
        # Bài thật: 43-cmt-huong007th trả lời 42-cmt-mza-phwn, cả hai nằm trên trang bài
        # gốc và 43 thụt lề vào ~40px.
        post = dict(comment('ROOT', 300, 0, None), handle='ens_dahy', image='post/ROOT.png', left=100)
        parent = dict(comment('DMb-H9kypXS', 120, 1), handle='_mza.phwn',
                      image='post/42.png', left=100, replies=1)
        child = dict(comment('DMcBSzezXe_', 9, 2), handle='huong007th',
                     image='post/43.png', left=141)
        tr.mark_parents([post, parent, child])
        result, _ = tr.collect([parent, child], post, lambda url: self.fail('không mở trang reply'),
                               max_depth=1, root_limit=20, per_parent=2)
        headers = [line for line in ts.build_editable_script(
            {'post': post, 'comments': result}).splitlines() if line.startswith('#')]
        self.assertEqual([line.split()[1] for line in headers],
                         ['post/ROOT.png', 'post/42.png', 'post/43.png'])
        self.assertNotIn('↳', headers[1])
        self.assertIn('reply · ↳ @_mza.phwn', headers[2])

    def test_old_min_like_setting_is_removed(self):
        options = threads_options.clean_options({'reply_min_likes': 1000, 'reply_per_parent': 3})
        self.assertNotIn('reply_min_likes', options)
        self.assertEqual(options['reply_per_parent'], 3)
