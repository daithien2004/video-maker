"""Browser smoke test against an already running local API; no external publishing."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from videomaker.paths import configure_browser_temp

from playwright.sync_api import expect, sync_playwright


def main():
    configure_browser_temp()
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:7861')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'work/ui-qa'
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        page.route('**/api/editorial/history', lambda route: route.fulfill(json={'items': []}))
        page.route('**/api/editorial/save', lambda route: route.fulfill(json={'id': 'qa-save', 'updated': 1793149200}))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.get_by_role('heading', name='Biến kịch bản thành câu chuyện.')).to_be_visible()
        assert page.locator('[data-slot="button"]').count() > 0, 'shadcn buttons were not mounted'
        page.get_by_role('button', name='Chuyển giao diện tối', exact=True).click()
        expect(page.locator('html')).to_have_class(re.compile('dark'))
        page.reload()
        expect(page.get_by_role('heading', name='Biến kịch bản thành câu chuyện.')).to_be_visible()
        expect(page.locator('html')).to_have_class(re.compile('dark'))
        page.screenshot(path=str(output / 'dark-theme.png'), full_page=True)
        page.get_by_role('button', name='Chuyển giao diện sáng', exact=True).click()
        expect(page.locator('html')).not_to_have_class(re.compile('dark'))
        page.get_by_label('Tên nội dung', exact=False).fill('ui-qa')
        page.get_by_label('Kịch bản video', exact=True).fill('[cuoi] Xin chào mọi người. || XIN *CHÀO* MỌI NGƯỜI.')
        page.get_by_role('button', name='Phân tích kịch bản', exact=True).click()
        expect(page.get_by_label('Lời đọc', exact=True)).to_have_value('Xin chào mọi người.')
        page.get_by_role('button', name='Chọn media nhịp 1', exact=True).click()
        dialog = page.get_by_role('dialog')
        expect(dialog.locator('.media-thumb').first).to_be_visible()
        dialog.locator('.media-thumb').first.click()
        expect(dialog).not_to_be_visible()
        expect(page.get_by_label('File media', exact=True)).to_have_value(re.compile(r'^assets/'))
        page.get_by_role('button', name='Xem khung nhịp 1', exact=True).click()
        expect(page.locator('.phone-frame img')).to_be_visible(timeout=60000)
        assert page.locator('.phone-frame img').evaluate('(img) => img.complete && img.naturalWidth > 0')
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)

        page.get_by_role('button', name='Thiết lập video', exact=True).click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.get_by_role('dialog').get_by_label('Tốc độ đọc', exact=False).press('ArrowRight')
        music = page.get_by_role('dialog').get_by_role('switch', name='Dùng nhạc nền', exact=True)
        checked = music.is_checked()
        music.click()
        assert music.is_checked() != checked
        page.get_by_role('button', name='Áp dụng', exact=True).click()
        page.get_by_role('button', name='Thiết lập video', exact=True).click()
        page.keyboard.press('Escape')
        expect(page.get_by_role('dialog')).not_to_be_visible()
        expect(page.get_by_role('button', name='Thiết lập video', exact=True)).to_be_focused()

        # Saving is intercepted so the user's saved script/config is untouched.
        saved = []
        def save(route):
            saved.append(route.request.post_data_json)
            route.fulfill(json={'message': 'Saved by smoke test'})
        page.route('**/api/settings', save)
        page.get_by_role('button', name='Lưu cấu hình', exact=True).click()
        expect(page.get_by_role('status').filter(has_text='Đã lưu kịch bản')).to_be_visible()
        assert saved[0]['settings']['content'] == 'ui-qa'
        assert saved[0]['settings']['speed'] > 0

        nav = page.get_by_role('navigation', name='Điều hướng chính')
        nav.get_by_role('button', name='Thư viện media', exact=True).click()
        expect(page.locator('.media-card').first).to_be_visible()
        page.get_by_role('textbox', name='Tìm media', exact=True).fill('Facepalm')
        expect(page.locator('.media-card')).to_have_count(1)
        nav.get_by_role('button', name=re.compile(r'Video đã xuất')).click()
        expect(page.locator('.output-card').first).to_be_visible()
        video_name = page.locator('.output-card h3').first.inner_text()
        page.locator('.output-thumb').first.click()
        video = page.get_by_role('dialog').locator('video')
        expect(video).to_be_visible()
        page.wait_for_function('document.querySelector("[role=dialog] video").readyState >= 1', timeout=20000)
        video.evaluate('(video) => { video.currentTime = 1; video.pause(); }')
        page.get_by_role('button', name='Chuẩn bị đăng Reel', exact=True).click()
        expect(page.get_by_role('combobox', name='Video đã xuất', exact=True)).to_have_value(re.compile(re.escape(video_name)))
        page.get_by_label('Caption', exact=True).fill('Bản caption đang chỉnh, cần giữ khi chuyển màn hình.')
        page.get_by_role('button', name='Kết nối Page', exact=True).click()
        expect(page.get_by_label('Page access token', exact=False)).to_have_value('')
        nav.get_by_role('button', name='Threads', exact=True).click()
        expect(page.get_by_role('heading', name='Một cuộc trò chuyện. Một video.')).to_be_visible()
        expect(page.get_by_label('Link bài viết', exact=True)).to_be_visible()
        nav.get_by_role('button', name='Video thường', exact=True).click()
        expect(page.get_by_label('Lời đọc', exact=True)).to_have_value('Xin chào mọi người.')
        nav.get_by_role('button', name='Facebook Reels', exact=True).click()
        page.get_by_role('button', name='Một video', exact=True).click()
        expect(page.get_by_label('Caption', exact=True)).to_have_value('Bản caption đang chỉnh, cần giữ khi chuyển màn hình.')
        nav.get_by_role('button', name='Video thường', exact=True).click()

        # Preview action is intercepted; the UI still plays a real existing export.
        files = page.request.get(args.url + '/api/outputs').json()['items']
        result = {'status': 'done', 'id': 'qa-render', 'kind': 'preview', 'progress': 1,
                  'result': {'file': files[0], 'preview': True, 'message': 'QA preview ready'}}
        page.route('**/api/render', lambda route: route.fulfill(json={'id': 'qa-render'}))
        page.route('**/api/jobs/qa-render', lambda route: route.fulfill(json=result))
        page.get_by_role('button', name='Dựng bản xem thử', exact=True).click()
        expect(page.locator('.phone-frame video')).to_be_visible()
        expect(page.locator('.job-bar')).to_have_count(0)
        page.wait_for_function('document.querySelector(".phone-frame video").readyState >= 1', timeout=20000)
        page.locator('.phone-frame video').evaluate('(video) => { video.currentTime = 1; video.pause(); }')

        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(output / 'mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Editor overflows mobile width'
        for name in ['Thư viện media', 'Video đã xuất', 'Facebook Reels', 'Threads']:
            nav.get_by_role('button', name=re.compile('^' + name)).click()
            page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), name + ' overflows mobile width'

        # Manual editorial stages use a text-only fixture and do not alter real source files.
        nav.get_by_role('button', name='Biên tập Threads', exact=True).click()
        expect(page.get_by_role('heading', name='Mở bài đã scan hoặc lấy bài mới', exact=True)).to_be_visible()
        source = {'content': 'qa-text-only', 'post': {'id': 'ROOT', 'image': 'post/main.png', 'text': 'Bài nguyên văn.'},
                  'comments': [{'id': 'P', 'parent_id': 'ROOT', 'depth': 1, 'image': 'post/parent.png',
                                'text': 'Đúng rồi.', 'datetime': '2026-10-28T01:00:00Z'},
                               {'id': 'R', 'parent_id': 'P', 'depth': 2, 'image': 'post/reply.png',
                                'text': 'Sao lại không?', 'datetime': '2026-10-28T01:01:00Z'}], 'images': []}
        prepared = page.request.post(args.url + '/api/editorial/prepare', data={'source_json': json.dumps(source, ensure_ascii=False)}).json()
        raw = {'session': prepared['session'], 'content': 'qa-text-only', 'script': prepared['seed'], 'images': [], 'comments': [], 'stats': {}}
        page.route('**/api/threads/scrape', lambda route: route.fulfill(json={'id': 'qa-threads'}))
        page.route('**/api/jobs/qa-threads', lambda route: route.fulfill(json={'id': 'qa-threads', 'kind': 'threads', 'status': 'done', 'progress': 1, 'result': raw}))
        nav.get_by_role('button', name='Threads', exact=True).click()
        page.get_by_label('Link bài viết', exact=True).fill('https://www.threads.com/@qa/post/test')
        page.get_by_role('button', name='Lấy bài', exact=True).click()
        expect(page.get_by_label('Kịch bản thô nhận từ Threads', exact=True)).to_have_value(re.compile('Bài nguyên văn'))
        nav.get_by_role('button', name='Threads', exact=True).click()
        expect(page.get_by_label('Kịch bản video', exact=True)).to_have_value('')
        expect(page.get_by_label('Kịch bản video', exact=True)).to_have_attribute('readonly', '')
        nav.get_by_role('button', name='Biên tập Threads', exact=True).click()
        page.get_by_role('button', name='Prepare & sang Done', exact=True).click()
        page.get_by_role('button', name='Bắt đầu từ bản thô', exact=True).click()
        expect(page.get_by_label('Bản đã sửa để dựng video', exact=True)).to_have_value(re.compile('Đúng rồi'))
        page.get_by_role('button', name='Kiểm tra bản đã sửa', exact=True).click()
        expect(page.get_by_role('heading', name='Chưa đạt — cần sửa lỗi', exact=True)).to_be_visible()
        page.get_by_role('switch', name='Kiểm tra file ảnh trong thư viện trên máy', exact=True).click()
        page.get_by_role('button', name='Kiểm tra lại', exact=True).click()
        expect(page.get_by_role('heading', name='Đạt cấu trúc — còn phần cần rà', exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Editorial overflows mobile width'
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.screenshot(path=str(output / 'editorial.png'), full_page=True)
        browser.close()
    if errors:
        raise AssertionError('\n'.join(errors))
    print(json.dumps({'result': 'passed', 'screenshots': str(output),
                      'checks': ['analysis', 'media-picker', 'real-frame', 'settings', 'library-search',
                                 'video-playback-and-seek', 'publish-selection', 'threads',
                                 'draft-preservation', 'preview-job', 'mobile-layout', 'shadcn-dialog-switch',
                                 'theme-persistence', 'manual-editorial-flow']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
