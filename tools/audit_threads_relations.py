"""Read saved comment detail pages to audit reply links, without changing the scan or login."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from videomaker import threads_shot as ts, threads_replies as tr, comment_manager as cm
from videomaker.paths import configure_browser_temp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Saved threads.json to inspect; never overwritten')
    parser.add_argument('--target', action='append', help='Optional comment IDs; omit to inspect all saved comments')
    parser.add_argument('--report-dir', type=Path, default=ts.WORK_DIR / 'threads-relation-audit')
    args = parser.parse_args()
    configure_browser_temp()
    source = json.loads(args.source.read_text(encoding='utf-8'))
    targets = [item for item in source['comments'] if not args.target or tr.post_id(item) in args.target]
    report = []
    directory = args.report_dir
    directory.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        settings = dict(viewport={'width': ts.VIEW_W, 'height': ts.VIEW_H}, locale='vi-VN', user_agent=ts.UA)
        if ts.STATE_FILE.exists():
            settings['storage_state'] = str(ts.STATE_FILE)
        context = browser.new_context(**settings)
        try:
            page = context.new_page()
            for target in targets:
                entry = {'target': tr.post_id(target), 'url': target.get('url')}
                try:
                    if not tr.safe_thread_url(target.get('url')):
                        raise ValueError('Missing or unsafe Threads URL')
                    page.goto(target['url'], wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_timeout(2200)
                    collected = {}
                    for _ in range(2):
                        ts.dismiss_overlays(page)
                        tr.expand_reply_buttons(page)
                        for raw in page.evaluate(ts.EXTRACT_JS):
                            item = ts.card_from_raw(raw)
                            if item:
                                collected[tr.post_id(item) or (item['handle'], item['text'][:60])] = item
                        page.mouse.wheel(0, ts.SCROLL_PX)
                        page.wait_for_timeout(ts.SCROLL_WAIT)
                    cards = list(collected.values())
                    focused = tr.focused_replies(target['url'], cards)
                    entry.update(title=page.title(), cards=cards, focused_ids=[tr.post_id(item) for item in focused] if focused is not None else None)
                    page.screenshot(path=str(directory / (target['id'] + '.png')))
                    print(json.dumps({'target': target['id'],
                                      'cards': [{'id': tr.post_id(item), 'handle': item['handle'], 'likes': item['likes']} for item in cards],
                                      'focused_ids': entry['focused_ids']}, ensure_ascii=True), flush=True)
                except Exception as error:
                    entry['error'] = str(error)
                    print(json.dumps({'target': target['id'], 'error': str(error)}, ensure_ascii=True), flush=True)
                report.append(entry)
                (directory / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        finally:
            context.close()
            browser.close()
    (directory / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    known = {tr.post_id(item) for item in source['comments']}
    pages = {entry['url']: tr.observed_thread(entry['url'], entry['cards'], source['post'])
             for entry in report if 'cards' in entry}
    def observed(url):
        cards = pages.get(url)
        return tr.ThreadPage([card for card in cards if tr.post_id(card) in known], cards.ancestors) if cards is not None else None
    comments, stats = tr.collect(source['comments'], source['post'], observed,
                                 max_depth=4, max_pages=len(source['comments']), per_parent=None, root_limit=0)
    before = {tr.post_id(item): item for item in source['comments']}
    changes = []
    proposed = copy.deepcopy(source)
    for item in comments:
        if item['id'] not in before:
            continue
        original = before[item['id']]
        if item.get('parent_id') != original.get('parent_id') and item['parent_id'] != tr.post_id(source['post']):
            changes.append({'id': item['id'], 'image': original.get('image'),
                            'old_parent': original.get('parent_id'), 'new_parent': item['parent_id'],
                            'parent_url': item['parent_url'], 'depth': item['depth']})
            target = next(comment for comment in proposed['comments'] if tr.post_id(comment) == item['id'])
            target.update({key: item.get(key) for key in ('parent_id', 'parent_url', 'parent_handle', 'depth', 'relation')})
    proposed['comments'] = cm.chronological(proposed['comments'])
    image_order = [proposed['post']['image']] + [item['image'] for item in proposed['comments']]
    images = {item['rel']: item for item in proposed.get('images', [])}
    proposed['images'] = [images[image] for image in image_order if image in images]
    (directory / 'changes.json').write_text(json.dumps({'changes': changes, 'stats': stats}, ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / 'proposed-source.json').write_text(json.dumps(proposed, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'observed_pages': len(pages), 'confirmed_corrections': changes}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
