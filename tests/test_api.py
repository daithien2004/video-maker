"""API contracts, file boundaries and jobs, without real TTS or external posting."""
import json
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from videomaker import api, app as actions, pipeline as pl


class LocalAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        dirs = {'ASSETS': 'assets', 'MEME_DIR': 'assets/memes', 'ILLUS_DIR': 'assets/illus',
                'BG_DIR': 'assets/backgrounds', 'MUSIC_DIR': 'assets/music', 'FONT_DIR': 'assets/fonts',
                'OUT_DIR': 'output', 'WORK_DIR': 'work', 'CACHE_DIR': 'work/cache'}
        for name, relative in dirs.items():
            directory = self.root / relative
            directory.mkdir(parents=True, exist_ok=True)
            self.stack.enter_context(patch.object(pl, name, directory))
        self.stack.enter_context(patch.object(api, 'APP_DIR', self.root))
        self.stack.enter_context(patch.dict(api.LIBRARIES, {
            'meme': pl.MEME_DIR, 'illus': pl.ILLUS_DIR, 'bg': pl.BG_DIR,
            'music': pl.MUSIC_DIR, 'font': pl.FONT_DIR}))
        config = self.root / 'config/settings.json'
        config.parent.mkdir()
        config.write_text(json.dumps({**actions.DEFAULTS, 'backend': 'dummy', 'content': ''}), encoding='utf-8')
        self.stack.enter_context(patch.object(actions, 'SETTINGS_FILE', config))
        self.secret = 'private-token-not-for-the-browser'
        self.stack.enter_context(patch.object(api.fb, 'load_config', return_value={
            'page_id': '1234', 'token': self.secret, 'version': 'v24.0'}))
        self.stack.enter_context(patch.object(api.fb, 'posted_log', return_value={'done.mp4': {'id': '1'}}))
        (pl.WORK_DIR / 'fb.env').write_text('FB_PAGE_TOKEN=' + self.secret)
        self.video = pl.OUT_DIR / 'done.mp4'
        self.video.write_bytes(b'0123456789abcdef')
        (self.root / 'frontend/dist').mkdir(parents=True)
        (self.root / 'frontend/dist/index.html').write_text('<html>React UI</html>')
        self.application = api.create_app()
        self.client = TestClient(self.application, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.application.state.jobs.pool.shutdown(wait=True)
        self.stack.close()
        self.temp.cleanup()

    def wait_job(self, key):
        for _ in range(200):
            result = self.client.get('/api/jobs/' + key).json()
            if result['status'] in ('done', 'error'):
                return result
            time.sleep(.005)
        self.fail('Job did not finish')

    def test_react_page_and_bootstrap_do_not_expose_token(self):
        self.assertIn('React UI', self.client.get('/').text)
        response = self.client.get('/api/bootstrap')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.secret, response.text)
        self.assertTrue(response.json()['facebook']['configured'])

    def test_media_supports_video_range_requests(self):
        response = self.client.get('/api/media', params={'path': 'output/done.mp4'}, headers={'Range': 'bytes=0-3'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b'0123')
        self.assertEqual(response.headers['content-range'], 'bytes 0-3/16')

    def test_media_rejects_secrets_and_paths_outside_library(self):
        for path in ('work/fb.env', 'config/settings.json', '../outside.mp4'):
            self.assertEqual(self.client.get('/api/media', params={'path': path}).status_code, 403)

    def test_foreign_origin_and_host_cannot_use_local_api(self):
        self.assertEqual(self.client.get('/api/bootstrap', headers={'Origin': 'https://example.org'}).status_code, 403)
        self.assertEqual(self.client.get('/api/bootstrap', headers={'Host': 'example.org'}).status_code, 403)

    def test_script_analysis_and_settings_stay_in_new_layout(self):
        response = self.client.post('/api/analyze', json={'script': '[sun] Xin chào. || XIN *CHÀO*', 'settings': {'content': ''}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['rows'][0][1], 'Xin chào.')
        response = self.client.post('/api/settings', json={'script': 'Bản đã lưu', 'settings': {'speed': 1.1, 'content': ''}})
        self.assertEqual(response.status_code, 200)
        cfg = json.loads(actions.SETTINGS_FILE.read_text(encoding='utf-8'))
        self.assertEqual(cfg['script'], 'Bản đã lưu')
        self.assertEqual(cfg['speed'], 1.1)
        self.assertFalse((self.root / 'settings.json').exists())

    def test_upload_and_delete_only_target_asset_files(self):
        response = self.client.post('/api/library/upload', data={'kind': 'illus', 'tag': 'sun', 'content': 'space'},
                                    files=[('files', ('photo.png', b'png-bytes', 'image/png'))])
        self.assertEqual(response.status_code, 200)
        path = response.json()['items'][0]['path']
        self.assertTrue(path.startswith('assets/illus/space/sun/'))
        self.assertEqual(self.client.delete('/api/library', params={'path': 'output/done.mp4'}).status_code, 403)
        self.assertEqual(self.client.delete('/api/library', params={'path': path}).status_code, 200)
        self.assertFalse((self.root / path).exists())
        self.assertTrue(self.video.exists())
        blocked = self.client.post('/api/library/upload', data={'kind': 'meme', 'tag': 'fun'},
                                   files=[('files', ('bad.exe', b'exe', 'application/octet-stream'))])
        self.assertEqual(blocked.status_code, 400)

    def test_job_uses_exact_selected_asset_and_returns_playable_url(self):
        image = pl.MEME_DIR / 'photo.png'
        image.write_bytes(b'png')
        captured = {}
        def render(rows, options, preview, cb):
            captured.update(rows=rows, preview=preview)
            cb(.5, 'Rendering')
            return self.video
        with patch.object(pl, 'render', side_effect=render):
            response = self.client.post('/api/render', json={'preview': True, 'settings': {'backend': 'dummy'},
                'rows': [[1, 'Xin chào', 'XIN CHÀO', '', 'assets/memes/photo.png']]})
            self.assertEqual(response.status_code, 200)
            result = self.wait_job(response.json()['id'])
        self.assertEqual(result['status'], 'done')
        self.assertEqual(Path(captured['rows'][0][4]), image.resolve())
        self.assertTrue(captured['preview'])
        self.assertEqual(self.client.get(result['result']['file']['url']).status_code, 200)

    def test_invalid_render_and_content_path_never_start_a_job(self):
        with patch.object(pl, 'render') as render:
            response = self.client.post('/api/render', json={'rows': [[1, 'Hi', 'HI', '', 'missing.png']]})
            self.assertEqual(response.status_code, 400)
            response = self.client.post('/api/settings', json={'settings': {'content': '../bad'}})
            self.assertEqual(response.status_code, 400)
            render.assert_not_called()

    def test_posted_status_uses_video_filename(self):
        result = self.client.get('/api/outputs').json()['items']
        self.assertTrue(result[0]['posted'])

    def test_facebook_schedule_is_explicit_queued_once_and_never_retried(self):
        with patch.object(actions, 'on_fb_schedule', side_effect=RuntimeError('upload failed ' + self.secret)) as send:
            response = self.client.post('/api/facebook/schedule', json={
                'video': 'output/done.mp4', 'caption': 'Test', 'now': True})
            result = self.wait_job(response.json()['id'])
            self.assertEqual(result['status'], 'error')
            self.assertNotIn(self.secret, result['message'])
            send.assert_called_once()

    def test_threads_rejects_unrelated_url_and_client_supplied_session(self):
        with patch.object(api.ts, 'run') as crawl:
            response = self.client.post('/api/threads/scrape', json={'url': 'https://example.org/post/1'})
            self.assertEqual(response.status_code, 400)
            crawl.assert_not_called()
        response = self.client.post('/api/threads/comments', json={'session': 'forged', 'action': 'delete'})
        self.assertEqual(response.status_code, 404)

    def test_saved_threads_source_keeps_reply_context_and_no_subtitles(self):
        directory = pl.ILLUS_DIR / 'demo/post'
        directory.mkdir(parents=True)
        state = {'content': 'demo', 'tag': 'post', 'dir': str(directory),
                 'json': str(directory / 'threads.json'), 'stats': {},
                 'post': {'id': 'ROOT', 'image': 'post/main.png', 'text': 'Original post', 'handle': 'author'},
                 'comments': [
                     {'id': 'P', 'image': 'post/parent.png', 'text': 'Parent comment', 'handle': 'parent', 'depth': 1, 'parent_id': 'ROOT'},
                     {'id': 'R', 'image': 'post/reply.png', 'text': 'Reply comment', 'handle': 'reply', 'depth': 2, 'parent_id': 'P'}],
                 'images': [{'rel': f'post/{name}.png', 'path': str(directory / f'{name}.png')}
                            for name in ('main', 'parent', 'reply')]}
        for image in state['images']:
            Path(image['path']).write_bytes(b'png')
        (directory / 'threads.json').write_text(json.dumps(state), encoding='utf-8')
        opened = self.client.post('/api/threads/open', json={'path': 'assets/illus/demo/post/threads.json'})
        self.assertEqual(opened.status_code, 200)
        session = opened.json()['session']
        script = '# post/main.png\nOriginal post || -\n# post/parent.png\nParent comment || -\n# post/reply.png\nReply comment || -'
        response = self.client.post('/api/analyze', json={'threads': True, 'session': session, 'script': script,
                                                        'settings': {'content': 'demo'}})
        self.assertEqual(response.status_code, 200)
        rows = response.json()['rows']
        self.assertEqual([row[2] for row in rows], ['-', '-', '-'])
        self.assertIn('@parent:', rows[-1][5])
        removed = self.client.post('/api/threads/comments', json={'session': session, 'script': script,
                                                                 'image': 'post/reply.png', 'action': 'delete'})
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(len(removed.json()['comments']), 1)
        self.assertTrue((directory / 'reply.png').is_file())

    def test_editorial_import_validates_text_without_changing_source_files(self):
        directory = pl.ILLUS_DIR / 'editorial/post'
        directory.mkdir(parents=True)
        image = directory / 'main.png'
        image.write_bytes(b'png')
        source = {'content': 'editorial', 'post': {'id': 'ROOT', 'image': 'post/main.png',
                  'text': 'Bài nguyên văn.', 'handle': 'author'}, 'comments': [], 'stats': {},
                  'images': [{'rel': 'post/main.png', 'path': str(image)}],
                  'dir': str(directory), 'json': str(directory / 'threads.json')}
        original = json.dumps(source, ensure_ascii=False)
        (directory / 'threads.json').write_text(original, encoding='utf-8')
        prepared = self.client.post('/api/editorial/prepare', json={'source_json': original})
        self.assertEqual(prepared.status_code, 200)
        self.assertIn('Bài nguyên văn.', prepared.json()['source_text'])
        session = prepared.json()['session']
        text = '# post/main.png\nBài nguyên văn. || -'
        payload = {'session': session, 'curated': text, 'cleaned': text}
        report = self.client.post('/api/editorial/validate', json=payload)
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()['status'], 'passed')
        used = self.client.post('/api/editorial/use', json=payload)
        self.assertEqual(used.status_code, 200)
        self.assertEqual(used.json()['rows'][0][2], '-')
        self.assertEqual((directory / 'threads.json').read_text(encoding='utf-8'), original)
        invalid = self.client.post('/api/editorial/validate', json={**payload, 'curated': text.replace('nguyên văn', 'đã sửa')})
        self.assertFalse(invalid.json()['valid'])
        transferred = self.client.post('/api/editorial/use', json={**payload, 'curated': text.replace('nguyên văn', 'đã sửa')})
        self.assertEqual(transferred.status_code, 200)

    def test_editorial_json_cannot_probe_media_outside_project(self):
        source = {'content': 'demo', 'post': {'id': 'ROOT', 'image': 'post/main.png', 'text': 'Bài.'},
                  'comments': [], 'images': [{'rel': 'post/main.png', 'path': str(self.root.parent / 'external.png')}]}
        prepared = self.client.post('/api/editorial/prepare', json={'source_json': json.dumps(source)})
        text = '# post/main.png\nBài. || -'
        payload = {'session': prepared.json()['session'], 'curated': text, 'cleaned': text}
        result = self.client.post('/api/editorial/validate', json=payload)
        self.assertFalse(result.json()['valid'])
        self.assertIn('missing_file', [issue['code'] for issue in result.json()['errors']])

    def test_editorial_checkpoint_survives_api_restart_and_saved_scan_reopening(self):
        directory = pl.ILLUS_DIR / 'resume/post'
        directory.mkdir(parents=True)
        image = directory / 'main.png'
        image.write_bytes(b'png')
        source = {'content': 'resume', 'post': {'id': 'ROOT', 'image': 'post/main.png', 'text': 'Bản thô.'},
                  'comments': [], 'images': [{'rel': 'post/main.png', 'path': str(image)}],
                  'json': str(directory / 'threads.json'), 'dir': str(directory)}
        (directory / 'threads.json').write_text(json.dumps(source), encoding='utf-8')
        prepared = self.client.post('/api/editorial/prepare', json={'source_json': json.dumps(source)}).json()
        text = '# post/main.png\nBản thô. || -'
        draft = {'raw_script': text, 'prepared_script': text, 'source_text': prepared['source_text'],
                 'curated': text, 'cleaned': 'Bản normalize đang sửa', 'stage': 2, 'check_images': True}
        saved = self.client.post('/api/editorial/save', json={'session': prepared['session'], 'draft': draft})
        self.assertEqual(saved.status_code, 200)
        key = saved.json()['id']
        self.client.close()
        self.application.state.jobs.pool.shutdown(wait=True)
        self.application = api.create_app()
        self.client = TestClient(self.application, raise_server_exceptions=False)
        history = self.client.get('/api/editorial/history').json()['items']
        self.assertEqual(history[0]['id'], key)
        restored = self.client.post('/api/editorial/restore', json={'id': key, 'kind': 'workspace'})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()['saved']['stage'], 2)
        self.assertEqual(restored.json()['saved']['cleaned'], 'Bản normalize đang sửa')
        reopened = self.client.post('/api/editorial/prepare', json={'source_json': json.dumps(source),
                                       'script': text, 'prefer_saved': True})
        self.assertEqual(reopened.json()['saved']['cleaned'], 'Bản normalize đang sửa')


    def test_export_deletion_removes_companion_but_rejects_assets(self):
        companion = self.video.with_suffix('.json')
        companion.write_text(json.dumps({'content': 'demo'}))
        video_path = self.video.relative_to(self.root).as_posix()
        plan = self.client.get('/api/outputs/related', params={'path': video_path})
        self.assertEqual(plan.status_code, 200, plan.text)
        self.assertEqual(len(plan.json()['files']), 2)
        response = self.client.delete('/api/outputs', params={'path': video_path})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(self.video.exists())
        self.assertFalse(companion.exists())
        asset = pl.BG_DIR / 'shared.mp4'
        asset.write_bytes(b'keep')
        response = self.client.delete('/api/outputs', params={'path': asset.relative_to(self.root).as_posix()})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(asset.exists())

    def test_scan_options_persist_without_changing_script(self):
        before = actions.load_settings()
        options = {'top': 35, 'mode': 'card', 'ident': 'anon', 'nested': True,
                   'reply_depth': 2, 'reply_min_likes': 5, 'reply_per_parent': 4}
        response = self.client.post('/api/threads/options', json=options)
        self.assertEqual(response.status_code, 200, response.text)
        restored = TestClient(api.create_app()).get('/api/bootstrap').json()['settings']
        self.assertEqual(restored['threads_scrape'], options)
        self.assertEqual(restored['script'], before['script'])
        self.assertEqual(restored['voice'], before['voice'])
        self.assertEqual(self.client.post('/api/threads/options', json={'top': -1}).status_code, 400)
        self.assertEqual(actions.load_settings()['threads_scrape'], options)

    def test_threads_raw_and_edited_scripts_survive_restart_and_empty_edit(self):
        directory = pl.ILLUS_DIR / 'saved/post'
        directory.mkdir(parents=True)
        source = {'content': 'saved', 'json': str(directory / 'threads.json'),
                  'post': {'id': 'ROOT', 'text': 'Original', 'image': 'post/main.png'},
                  'comments': [], 'images': []}
        (directory / 'threads.json').write_text(json.dumps(source), encoding='utf-8')
        path = 'assets/illus/saved/post/threads.json'
        opened = self.client.post('/api/threads/open', json={'path': path}).json()
        original = opened['script']
        edited = '# post/main.png\nEdited version || -'
        saved = self.client.post('/api/threads/save-script', json={
            'session': opened['session'], 'script': edited})
        self.assertEqual(saved.status_code, 200, saved.text)
        restarted = TestClient(api.create_app())
        restored = restarted.post('/api/threads/open', json={'path': path}).json()
        self.assertEqual(restored['raw_script'], original)
        self.assertEqual(restored['edited_script'], edited)
        self.assertEqual(restored['script'], original)
        restarted.post('/api/threads/save-script', json={'session': restored['session'], 'script': ''})
        restored = restarted.post('/api/threads/open', json={'path': path}).json()
        self.assertEqual(restored['edited_script'], '')
        self.assertEqual(restored['raw_script'], original)


if __name__ == '__main__':
    unittest.main()
