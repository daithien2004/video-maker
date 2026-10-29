"""Local HTTP API and React frontend for the existing video pipeline."""
from __future__ import annotations

import json
import copy
import hashlib
import mimetypes
import os
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import anyio
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import app as actions
from . import fb_post as fb
from . import pipeline as pl
from . import threads_shot as ts
from . import threads_editorial as editorial
from .editorial_store import EditorialStore, ThreadsScriptStore
from .threads_preview import preview_items
from .paths import APP_DIR, configure_browser_temp

MEDIA_EXT = pl.VIDEO_EXT | pl.IMAGE_EXT | pl.AUDIO_EXT | {'.ttf', '.otf', '.ttc'}
LIBRARIES = {'meme': pl.MEME_DIR, 'illus': pl.ILLUS_DIR, 'bg': pl.BG_DIR,
             'music': pl.MUSIC_DIR, 'font': pl.FONT_DIR}
LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1', 'testserver'}


def message(error: Exception) -> str:
    text = str(getattr(error, 'message', None) or error)
    token = fb.load_config().get('token') or ''
    return text.replace(token, '[token]') if len(token) > 8 else text


def media_path(value: str, *, library_only=False) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else APP_DIR / path).resolve()
    roots = [pl.ASSETS] if library_only else [pl.ASSETS, pl.OUT_DIR, pl.WORK_DIR]
    if not any(root.resolve() in path.parents for root in roots):
        raise HTTPException(403, 'Đường dẫn nằm ngoài thư viện media.')
    if path.suffix.lower() not in MEDIA_EXT:
        raise HTTPException(403, 'Loại file không được phép truy cập.')
    if not path.is_file():
        raise HTTPException(404, 'File không còn tồn tại.')
    return path


def file_info(path: Path) -> dict:
    relative = path.resolve().relative_to(APP_DIR).as_posix()
    stat = path.stat()
    return {'path': relative, 'name': path.name, 'size': stat.st_size,
            'modified': stat.st_mtime, 'url': '/api/media?path=' + quote(relative, safe=''),
            'type': mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}


THUMB_DIR = pl.WORK_DIR / 'thumbs'

_WIN_READ = 0x80000000
_WIN_SHARE_ALL = 0x1 | 0x2 | 0x4
_WIN_OPEN_EXISTING = 3
_WIN_ATTR_NORMAL = 0x80


def _open_shared(path: str):
    """Cho phép xóa/đổi tên file khi trình duyệt còn đang đọc (Windows khóa file đang mở)."""
    if os.name != 'nt':
        return anyio.wrap_file(open(path, 'rb'))
    import ctypes
    import msvcrt
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    handle = kernel32.CreateFileW(str(path), _WIN_READ, _WIN_SHARE_ALL, None,
                                  _WIN_OPEN_EXISTING, _WIN_ATTR_NORMAL, None)
    if handle == wintypes.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), f'Không mở được file media: {path}')
    fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, 'O_BINARY', 0))
    return anyio.wrap_file(os.fdopen(fd, 'rb'))


class MediaResponse(FileResponse):
    @asynccontextmanager
    async def _open_file(self):
        file = await anyio.to_thread.run_sync(_open_shared, str(self.path))
        try:
            yield file
        finally:
            with anyio.CancelScope(shield=True):
                await file.aclose()


def poster_url(video: Path) -> str:
    relative = video.resolve().relative_to(APP_DIR).as_posix()
    return '/api/media/thumb?path=' + quote(relative, safe='')


def _thumb_key(video: Path) -> str:
    relative = video.resolve().relative_to(APP_DIR).as_posix()
    return hashlib.sha1(relative.encode('utf-8')).hexdigest()[:12]


def poster_image(video: Path) -> Path:
    """Ảnh xem trước cho thẻ video; giữ file MP4 khỏi bị khóa khi duyệt thư viện."""
    stamp = int(video.stat().st_mtime)
    target = THUMB_DIR / f'{_thumb_key(video)}-{stamp}.jpg'
    if target.is_file():
        return target
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    temp = THUMB_DIR / f'{target.stem}-{os.getpid()}-{threading.get_ident()}.jpg'
    try:
        pl.run_ffmpeg(['-ss', '0.5', '-i', str(video), '-frames:v', '1',
                       '-vf', "scale='min(540,iw)':-2", '-q:v', '4', str(temp)],
                      THUMB_DIR, stall=20)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def settings_with(updates: dict) -> dict:
    cfg = actions.load_settings()
    for key, value in updates.items():
        if key in actions.DEFAULTS:
            clean = actions._clean(key, value)
            if clean is not None:
                cfg[key] = clean
    content = cfg.get('content', '')
    if content and (Path(content).name != content or content in {'.', '..'} or '/' in content or '\\' in content):
        raise HTTPException(400, 'Tên nội dung không được chứa đường dẫn.')
    return cfg


def options(cfg: dict, threads=False):
    values = [cfg[k] for k in actions.OPT_KEYS]
    return actions.threads_opts(cfg['content'], *values) if threads else actions.make_opts(*values)


def resolve_row_clip(value: str, content: str):
    # Library picker returns project-relative paths; the renderer accepts absolute paths.
    if value.replace('\\', '/').startswith('assets/'):
        return media_path(value)
    return pl.resolve_clip(value, content)


def validate_rows(rows: list[list], content: str, threads: bool = False):
    if not rows or len(rows) > 2000:
        raise HTTPException(400, 'Cần từ 1 đến 2.000 nhịp để dựng video.')
    for row in rows:
        if len(row) not in (5, 6, 7):
            raise HTTPException(400, 'Mỗi nhịp cần lời đọc và đủ 5 cột dữ liệu.')
        if not str(row[1] or '').strip():
            if threads and row[4]:
                row[1], row[2] = '[sound]', '-'
            else:
                raise HTTPException(400, 'Nhịp thiếu lời đọc hoặc ảnh.')
        if threads and row[1] in ('[sound]', '[zoom]') and not row[4]:
            raise HTTPException(400, 'Nhịp âm thanh cần có ảnh.')
        if threads and len(row) > 6 and str(row[6] or '').strip() and not row[4]:
            raise HTTPException(400, 'Nhịp zoom cần có ảnh.')
        if row[4]:
            clip = resolve_row_clip(str(row[4]), content)
            if not clip:
                raise HTTPException(400, f'Không tìm thấy media: {row[4]}')
            row[4] = str(media_path(str(clip)))


def decorate_rows(rows: list[list], content: str) -> list[dict]:
    result = []
    for row in rows:
        clip = resolve_row_clip(str(row[4] or ''), content)
        item = None
        if clip:
            try:
                item = file_info(media_path(str(clip)))
            except HTTPException:
                pass
        result.append({'row': row, 'media': item})
    return result


class Jobs:
    """One expensive operation at a time, bounded queue, no automatic retries."""
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='videomaker')
        self.items: dict[str, dict] = {}
        self.lock = threading.Lock()

    def submit(self, kind, fn):
        with self.lock:
            if sum(j['status'] in ('queued', 'running') for j in self.items.values()) >= 12:
                raise HTTPException(429, 'Có nhiều tác vụ đang chờ. Vui lòng đợi.')
            if len(self.items) >= 100:
                for key in list(self.items):
                    if self.items[key]['status'] in ('done', 'error'):
                        del self.items[key]
                        break
            key = uuid.uuid4().hex
            self.items[key] = {'id': key, 'kind': kind, 'status': 'queued', 'progress': 0,
                               'message': 'Đang chờ xử lý…', 'created': time.time()}

        def progress(value=0, desc='', **_):
            with self.lock:
                self.items[key].update(progress=max(0, min(1, float(value))), message=str(desc))

        def run():
            with self.lock:
                self.items[key].update(status='running', message='Đang xử lý…')
            try:
                result = fn(progress)
                with self.lock:
                    self.items[key].update(status='done', progress=1, message='Hoàn tất', result=result)
            except Exception as error:
                with self.lock:
                    self.items[key].update(status='error', message=message(error))

        self.pool.submit(run)
        return {'id': key}

    def get(self, key):
        with self.lock:
            if key not in self.items:
                raise HTTPException(404, 'Tác vụ không còn trong phiên máy chủ này.')
            return dict(self.items[key])


class Draft(BaseModel):
    script: str = Field(default='', max_length=250_000)
    settings: dict[str, Any] = Field(default_factory=dict)
    rows: list[list[Any]] = Field(default_factory=list, max_length=2000)
    threads: bool = False
    session: str = ''


class RenderRequest(Draft):
    preview: bool = True


class ScrapeRequest(BaseModel):
    url: str
    content: str = ''
    top: int = Field(default=20, ge=0, le=500)
    mode: str = 'auto'
    ident: str = 'avatar'
    nested: bool = True
    reply_depth: int = Field(default=1, ge=1, le=4)
    reply_min_likes: int = Field(default=10, ge=0)
    reply_per_parent: int = Field(default=2, ge=0, le=100)


class CommentRequest(BaseModel):
    session: str
    script: str = ''
    image: str = ''
    action: str


class ThreadsFrameRequest(BaseModel):
    session: str
    image: str
    text: str = Field(default='', max_length=2000)
    settings: dict[str, Any] = Field(default_factory=dict)
    zoom: bool = False


class EditorialPrepareRequest(BaseModel):
    path: str = ''
    session: str = ''
    source_json: str = Field(default='', max_length=2_000_000)
    script: str = Field(default='', max_length=500_000)
    prefer_saved: bool = False


class EditorialValidateRequest(BaseModel):
    session: str
    curated: str = Field(default='', max_length=500_000)
    cleaned: str = Field(default='', max_length=500_000)
    check_images: bool = True


class EditorialSaveRequest(BaseModel):
    session: str
    draft: dict[str, Any]


class EditorialRestoreRequest(BaseModel):
    id: str
    kind: str = 'workspace'


class FacebookRequest(BaseModel):
    page: str = ''
    token: str = ''
    version: str = ''
    tags: str = ''
    video: str = ''
    caption: str = ''
    when: str = ''
    now: bool = False
    post_id: str = ''
    videos: list[str] = Field(default_factory=list)
    pattern: str = '2/ngày'
    edits: list[list[Any]] | None = None
    source: str = ''
    topic: str = 'Tự nhận diện'


def create_app() -> FastAPI:
    api = FastAPI(title='VideoMaker Local API', docs_url='/api/docs')
    jobs = Jobs()
    editorial_store = EditorialStore(pl.WORK_DIR / 'threads-script' / 'sessions')
    script_store = ThreadsScriptStore(pl.WORK_DIR / 'threads-script' / 'video-drafts')
    sessions: dict[str, dict] = {}
    session_lock = threading.RLock()
    api.state.jobs = jobs

    @api.middleware('http')
    async def local_only(request: Request, call_next):
        if request.url.hostname not in LOCAL_HOSTS:
            return JSONResponse({'detail': 'Chỉ phục vụ ứng dụng trên máy này.'}, status_code=403)
        origin = request.headers.get('origin')
        if origin and (urlsplit(origin).hostname not in LOCAL_HOSTS or urlsplit(origin).scheme not in ('http', 'https')):
            return JSONResponse({'detail': 'Nguồn truy cập không được phép.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api/') else 'no-cache'
        return response

    @api.exception_handler(Exception)
    async def error_handler(_request, error):
        return JSONResponse({'detail': message(error)}, status_code=400)

    def remember(state):
        with session_lock:
            if len(sessions) >= 50:
                sessions.pop(next(iter(sessions)))
            key = uuid.uuid4().hex
            sessions[key] = state
            return key

    def get_session(key):
        with session_lock:
            if key not in sessions:
                raise HTTPException(404, 'Phiên bài đã hết. Mở lại bài từ danh sách đã lưu.')
            return sessions[key]

    def thread_result(state, script=None, key=None):
        return {'session': key or remember(state), 'content': state.get('content', ''),
                'script': script if script is not None else ts.build_editable_script(state),
                'comments': actions._threads_item_rows(state), 'stats': state.get('stats', {}),
                'images': [dict(rel=i['rel'], **file_info(media_path(i['path']))) for i in state.get('images', [])]}

    @api.get('/api/bootstrap')
    def bootstrap():
        config = fb.load_config()
        return {'api_revision': 5, 'settings': actions.load_settings(), 'defaults': actions.DEFAULTS,
                'backgrounds': actions.bg_choices(), 'contents': pl.list_contents(),
                'threads_status': ts.session_status().replace('**', ''),
                'facebook': {'page': config.get('page_id', ''), 'version': config.get('version', fb.DEFAULT_VERSION),
                             'tags': config.get('hashtags', ''), 'configured': bool(config.get('page_id') and config.get('token')),
                             'note': actions._fb_env_note(), 'suggested_time': actions._fb_suggest_time()},
                'counts': {'memes': sum(map(len, pl.scan_memes().values())),
                           'contents': len(pl.list_contents()), 'videos': len(list(pl.OUT_DIR.glob('*.mp4')))}}

    @api.post('/api/settings')
    def save_settings(body: Draft):
        cfg = settings_with(body.settings)
        actions.save_settings(**{**cfg, 'script': body.script})
        return {'message': 'Đã lưu kịch bản và cấu hình.'}

    @api.post('/api/analyze')
    def analyze(body: Draft):
        cfg = settings_with(body.settings)
        if body.threads:
            state = get_session(body.session) if body.session else None
            result = actions.on_threads_build(body.script, state)
            state, rows, note = result[:3]
            key = body.session or remember(state)
            with session_lock:
                sessions[key] = state
            content = state.get('content', '')
            return {'rows': rows, 'beats': decorate_rows(rows, content), 'message': note,
                    'session': key, 'content': content}
        rows, note = actions.on_analyze(body.script, cfg['content'])
        return {'rows': rows, 'beats': decorate_rows(rows, cfg['content']), 'message': note}

    @api.post('/api/render')
    def render(body: RenderRequest):
        cfg = settings_with(body.settings)
        validate_rows(body.rows, cfg['content'], threads=body.threads)
        opt = options(cfg, body.threads)

        def work(progress):
            out = pl.render(body.rows, opt, preview=body.preview, cb=lambda value, note: progress(value, desc=note))
            result = {'file': file_info(out), 'preview': body.preview, 'threads': body.threads,
                      'message': 'Bản xem thử đã sẵn sàng.' if body.preview else 'Đã xuất video hoàn chỉnh.'}
            if not body.preview:
                result['caption'], result['when'], result['note'] = actions._auto_schedule_draft(str(out))
            return result

        return jobs.submit('preview' if body.preview else 'export', work)

    @api.post('/api/frame')
    def frame(body: Draft):
        cfg = settings_with(body.settings)
        validate_rows(body.rows[:1], cfg['content'], threads=body.threads)
        row = body.rows[0]
        def work(_progress):
            opt = options(cfg, body.threads)
            sound = body.threads and row[1] in ('[sound]', '[zoom]')
            zoom = body.threads and (str(row[6] or '').strip() in ('1', 'true', 'on')
                                     if len(row) > 6 else row[1] == '[zoom]')
            text = '' if sound or zoom or row[2] == '-' else str(row[2] or row[1])
            image, chunks = pl.preview_frame(text, opt, str(row[4] or ''),
                                             str(row[5] or '') if len(row) > 5 else '',
                                             zoom=zoom)
            return {'file': file_info(image), 'chunks': chunks, 'threads': body.threads}
        return jobs.submit('frame', work)

    @api.post('/api/voices')
    def voices(body: Draft):
        cfg = settings_with(body.settings)
        return jobs.submit('voices', lambda _p: {'voices': pl.list_voices(cfg['backend'])})

    @api.post('/api/sample')
    def sample(body: Draft):
        cfg = settings_with(body.settings)
        return jobs.submit('sample', lambda _p: {'file': file_info(pl.synth(body.script.strip() or 'Xin chào, đây là giọng đọc thử.',
                                           cfg['backend'], cfg['voice'], cfg['speed']))})

    @api.get('/api/jobs/{key}')
    def get_job(key: str):
        return jobs.get(key)

    @api.get('/api/threads/preview-data')
    def threads_preview_data(session: str):
        source = get_session(session)
        items = preview_items(source)
        for item in items:
            path = item.pop('path') or str(pl.ILLUS_DIR / str(source.get('content') or '') / item['image'])
            try:
                item['file'] = file_info(media_path(path))
            except HTTPException:
                item['file'] = None
        return {'items': items, 'content': source.get('content') or ''}

    @api.post('/api/threads/frame')
    def threads_frame(body: ThreadsFrameRequest):
        source = get_session(body.session)
        item = next((item for item in preview_items(source) if item['image'] == body.image), None)
        if item is None:
            raise HTTPException(400, 'Ảnh được chọn không thuộc bài Threads đang làm.')
        path = media_path(item['path'] or str(pl.ILLUS_DIR / str(source.get('content') or '') / item['image']))
        if path.suffix.lower() not in pl.IMAGE_EXT:
            raise HTTPException(400, 'Khung Threads cần ảnh bài/comment đã scan.')
        cfg = settings_with({**body.settings, 'content': source.get('content') or ''})
        opt = options(cfg, threads=True)
        def work(_progress):
            image, chunks = pl.preview_frame('' if body.zoom else body.text.strip(), opt, str(path), item['context'], zoom=body.zoom)
            return {'file': file_info(image), 'chunks': chunks, 'threads': True,
                    'kind': item['kind'], 'context': item['parent_snippet']}
        return jobs.submit('frame', work)

    @api.get('/api/media')
    def media(path: str, download: bool = False):
        target = media_path(path)
        return MediaResponse(target, filename=target.name if download else None,
                             content_disposition_type='attachment' if download else 'inline')

    @api.get('/api/library')
    def library():
        items = []
        for kind, root in LIBRARIES.items():
            for path in sorted(root.rglob('*')):
                if not path.is_file() or path.suffix.lower() not in MEDIA_EXT:
                    continue
                try:
                    media_path(str(path), library_only=True)
                    rel = path.relative_to(root)
                    info = file_info(path)
                    if path.suffix.lower() in pl.VIDEO_EXT:
                        info['poster'] = '/api/media/thumb?path=' + quote(info['path'], safe='')
                    items.append(dict(kind=kind, tag=rel.parent.as_posix(), **info))
                except (ValueError, HTTPException):
                    continue
        return {'items': items}

    @api.post('/api/library/upload')
    def upload(kind: str = Form(...), tag: str = Form(''), content: str = Form(''),
               files: list[UploadFile] = File(...)):
        if kind not in LIBRARIES:
            raise HTTPException(400, 'Loại thư viện không hợp lệ.')
        if kind in ('meme', 'illus') and not tag.strip():
            raise HTTPException(400, 'Hãy nhập thẻ media.')
        if kind == 'illus' and not content.strip():
            raise HTTPException(400, 'Hãy nhập tên nội dung.')
        allowed = {'bg': pl.VIDEO_EXT, 'music': pl.AUDIO_EXT, 'font': {'.ttf', '.otf', '.ttc'},
                   'meme': pl.VIDEO_EXT | pl.IMAGE_EXT, 'illus': pl.VIDEO_EXT | pl.IMAGE_EXT}[kind]
        dest = LIBRARIES[kind]
        if kind == 'illus':
            dest /= actions.safe_name(content)
        if kind in ('meme', 'illus'):
            dest /= actions.safe_name(tag)
        if pl.ASSETS.resolve() not in dest.resolve().parents:
            raise HTTPException(403, 'Thư mục tải lên không hợp lệ.')
        for item in files:
            if Path(item.filename or '').suffix.lower() not in allowed:
                raise HTTPException(400, f'File không đúng loại: {item.filename}')
        dest.mkdir(parents=True, exist_ok=True)
        uploaded = []
        for item in files:
            suffix = Path(item.filename).suffix.lower()
            stem = actions.safe_name(Path(item.filename).stem) or 'media'
            target = dest / f'{stem}-{uuid.uuid4().hex[:8]}{suffix}'
            total = 0
            try:
                with target.open('xb') as out:
                    while chunk := item.file.read(1024 * 1024):
                        total += len(chunk)
                        if total > 1024 * 1024 * 1024:
                            raise HTTPException(413, 'Mỗi file tối đa 1 GB.')
                        out.write(chunk)
                if not total:
                    raise HTTPException(400, 'File tải lên đang trống.')
                uploaded.append(file_info(target))
            except Exception:
                target.unlink(missing_ok=True)
                raise
            finally:
                item.file.close()
        return {'items': uploaded, 'message': f'Đã thêm {len(uploaded)} file vào thư viện.'}

    @api.delete('/api/library')
    def delete_asset(path: str):
        target = media_path(path, library_only=True)
        target.unlink()
        return {'message': 'Đã xóa ' + target.name}

    @api.get('/api/outputs')
    def outputs():
        posted = fb.posted_log()
        return {'items': [dict(posted=bool(posted.get(p.name)), poster=poster_url(p), **file_info(p))
                          for p in sorted(pl.OUT_DIR.glob('*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)]}

    @api.get('/api/media/thumb')
    def media_thumb(path: str):
        target = media_path(path)
        if target.suffix.lower() not in pl.VIDEO_EXT:
            raise HTTPException(400, 'Chỉ tạo ảnh xem trước cho file video.')
        try:
            image = poster_image(target)
        except Exception as error:
            raise HTTPException(404, 'Chưa tạo được ảnh xem trước cho video này.') from error
        return FileResponse(image, media_type='image/jpeg')

    @api.get('/api/outputs/thumb')
    def output_thumb(path: str):
        return media_thumb(path)

    @api.get('/api/outputs/related')
    def output_related(path: str):
        from .output_cleanup import related_files
        try:
            files = related_files(media_path(path), pl.OUT_DIR)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {'files': [p.relative_to(APP_DIR).as_posix() for p in files]}

    @api.delete('/api/outputs')
    def delete_export(path: str):
        from .output_cleanup import delete_output
        target = media_path(path)
        try:
            deleted = delete_output(target, pl.OUT_DIR)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        except PermissionError as error:
            raise HTTPException(409, 'Video đang được phát hoặc đọc bởi chương trình khác. Đóng khung xem trước/trình phát rồi thử lại.') from error
        for thumb in THUMB_DIR.glob(f'{_thumb_key(target)}-*.jpg'):
            try:
                thumb.unlink(missing_ok=True)
            except PermissionError:
                pass
        return {'deleted': [p.relative_to(APP_DIR).as_posix() for p in deleted],
                'message': 'Đã xóa video và các file đi kèm trong output.'}

    @api.get('/api/threads/sources')
    def sources():
        return {'items': [{'label': label, 'path': str(Path(path).relative_to(APP_DIR).as_posix())}
                           for label, path in actions._fb_sources()]}

    @api.post('/api/threads/open')
    def open_source(body: dict):
        path = (APP_DIR / str(body.get('path', ''))).resolve()
        if pl.ILLUS_DIR.resolve() not in path.parents or path.name != 'threads.json' or not path.is_file():
            raise HTTPException(400, 'Không tìm thấy bài đã lưu.')
        state = json.loads(path.read_text(encoding='utf-8'))
        result = thread_result(state)
        target = script_store.path_for(script_store.key_for(state))
        if target.is_file():
            saved = script_store.load(target.stem)['draft']
            result.update(raw_script=saved['raw_script'], edited_script=saved['edited_script'])
        return result

    @api.post('/api/threads/save-script')
    def save_thread_script(body: Draft):
        state = get_session(body.session)
        target = script_store.path_for(script_store.key_for(state))
        raw = (script_store.load(target.stem)['draft']['raw_script'] if target.is_file()
               else ts.build_editable_script(state))
        result = script_store.save(state, {'raw_script': raw, 'edited_script': body.script})
        return {**result, 'message': 'Đã lưu bản thô và bản đã chỉnh.'}

    @api.post('/api/threads/scrape')
    def scrape(body: ScrapeRequest):
        url = urlsplit(body.url)
        if url.scheme not in ('https', 'http') or url.hostname not in ('threads.com', 'www.threads.com', 'threads.net', 'www.threads.net'):
            raise HTTPException(400, 'Hãy dùng link bài trên threads.com hoặc threads.net.')
        if body.mode not in ('auto', 'shot', 'card') or body.ident not in ('avatar', 'full', 'no-avatar', 'anon'):
            raise HTTPException(400, 'Chế độ ảnh không hợp lệ.')
        run = ts.Run(url=body.url, content=actions.safe_name(body.content) if body.content else '',
                     top=body.top, mode=body.mode, ident=body.ident, nested_replies=body.nested,
                     reply_depth=body.reply_depth, reply_min_likes=body.reply_min_likes,
                     reply_per_parent=body.reply_per_parent)
        return jobs.submit('threads', lambda progress: thread_result(ts.run(run, progress=progress)))

    @api.post('/api/threads/options')
    def save_scan_options(body: dict):
        from .threads_options import clean_options
        clean = clean_options(body)
        if clean is None:
            raise HTTPException(400, 'Tùy chọn lấy bài không hợp lệ.')
        cfg = actions.load_settings()
        actions.save_settings(**{**cfg, 'threads_scrape': clean})
        return {'options': clean, 'message': 'Đã lưu tùy chọn lấy bài.'}

    @api.post('/api/threads/login')
    def login():
        def work(progress):
            ts.save_login(progress=progress)
            return {'message': ts.session_status()}
        return jobs.submit('login', work)

    @api.post('/api/threads/logout')
    def logout():
        return {'message': actions.on_threads_logout()}

    @api.post('/api/threads/comments')
    def comments(body: CommentRequest):
        with session_lock:
            state = get_session(body.session)
            rows = actions._threads_item_rows(state)
            if body.action in ('likes', 'oldest', 'newest'):
                result = actions.on_threads_sort_commit(state, rows, body.script, body.action)
            elif body.action in ('up', 'down', 'delete'):
                result = actions.on_threads_comment_action(state, rows, body.script, body.image, body.action)
            else:
                raise HTTPException(400, 'Thao tác không hợp lệ.')
            sessions[body.session] = result[0]
            return thread_result(result[0], result[4], body.session)

    @api.post('/api/editorial/prepare')
    def prepare_editorial(body: EditorialPrepareRequest):
        if body.source_json.strip():
            try:
                state = json.loads(body.source_json.lstrip('\ufeff'))
            except ValueError as error:
                raise HTTPException(400, 'Không đọc được threads.json: ' + str(error)) from error
        elif body.session:
            state = copy.deepcopy(get_session(body.session))
        else:
            path = (APP_DIR / body.path).resolve()
            if pl.ILLUS_DIR.resolve() not in path.parents or path.name != 'threads.json' or not path.is_file():
                raise HTTPException(400, 'Chọn đúng bài Threads đã lưu hoặc mở file threads.json.')
            state = json.loads(path.read_text(encoding='utf-8-sig'))
        if '_editorial_origin' not in state:
            state['_editorial_origin'] = copy.deepcopy(state)
        checkpoint_key = editorial_store.key_for(state)
        if body.prefer_saved and editorial_store.path_for(checkpoint_key).is_file():
            checkpoint = editorial_store.load(checkpoint_key)
            state = checkpoint['source']
            return {**editorial.prepare_workspace(state), 'session': remember(state),
                    'saved': checkpoint['draft'], 'updated': checkpoint['updated']}
        if body.script.strip():
            state = editorial.source_from_draft(state, body.script)
        result = editorial.prepare_workspace(state)
        return {**result, 'session': remember(state)}

    @api.get('/api/editorial/history')
    def editorial_history():
        items = editorial_store.list_items()
        saved_ids = {item['id'] for item in items}
        for path in pl.ILLUS_DIR.glob('*/*/threads.json'):
            try:
                source = json.loads(path.read_text(encoding='utf-8-sig'))
                if not (source.get('post') or {}).get('image'):
                    continue
                if editorial_store.key_for(source) in saved_ids:
                    continue
                items.append({'id': path.relative_to(APP_DIR).as_posix(), 'kind': 'scan',
                              'label': source.get('content') or path.parent.parent.name,
                              'updated': path.stat().st_mtime, 'stage': 0, 'has_curated': False, 'has_cleaned': False})
            except (ValueError, OSError):
                continue
        return {'items': sorted(items, key=lambda item: item['updated'], reverse=True)}

    @api.post('/api/editorial/save')
    def save_editorial(body: EditorialSaveRequest):
        return editorial_store.save(get_session(body.session), body.draft)

    @api.post('/api/editorial/restore')
    def restore_editorial(body: EditorialRestoreRequest):
        if body.kind == 'workspace':
            checkpoint = editorial_store.load(body.id)
            state, saved = checkpoint['source'], checkpoint['draft']
        elif body.kind == 'scan':
            path = (APP_DIR / body.id).resolve()
            if pl.ILLUS_DIR.resolve() not in path.parents or path.name != 'threads.json' or not path.is_file():
                raise HTTPException(400, 'Không tìm thấy bài đã scan trong thư viện.')
            state = json.loads(path.read_text(encoding='utf-8-sig'))
            saved = None
        else:
            raise HTTPException(400, 'Loại phiên không hợp lệ.')
        result = editorial.prepare_workspace(state)
        origin = state.get('_editorial_origin') or state
        if '_editorial_origin' not in state:
            state['_editorial_origin'] = copy.deepcopy(state)
        raw_session = remember(copy.deepcopy(origin))
        origin_images = []
        for image in origin.get('images') or []:
            try:
                origin_images.append(dict(rel=image['rel'], **file_info(media_path(image['path']))))
            except (HTTPException, KeyError):
                continue
        return {**result, 'session': remember(state), 'saved': saved,
                'origin': {'session': raw_session, 'script': ts.build_editable_script(origin), 'content': origin.get('content') or '',
                           'images': origin_images, 'comments': actions._threads_item_rows(origin), 'stats': origin.get('stats') or {}},
                'updated': checkpoint.get('updated') if body.kind == 'workspace' else None}

    def editorial_report(body: EditorialValidateRequest, *, force_images=False):
        state = get_session(body.session)
        report = editorial.validate_workflow(state, body.curated, body.cleaned, require_images=False)
        if body.check_images or force_images:
            images = {i.get('rel'): i.get('path') for i in state.get('images') or []}
            for image in dict.fromkeys(report['images']):
                path = images.get(image)
                if not path:
                    path = str(pl.ILLUS_DIR / str(state.get('content') or '') / image)
                try:
                    media_path(path)
                except HTTPException:
                    report['errors'].append({'stage': 'cleaned', 'line': None, 'code': 'missing_file',
                                             'message': f'Không tìm thấy ảnh hợp lệ trong thư viện: {image}.'})
        else:
            report['warnings'].append({'stage': 'source', 'line': None, 'code': 'files_unchecked',
                                        'message': 'Chưa kiểm tra file ảnh trên máy. Sẽ kiểm tra lại trước khi dùng trong trình dựng.'})
        report['valid'] = not report['errors']
        report['status'] = 'error' if report['errors'] else 'review' if report['warnings'] else 'passed'
        return state, report

    @api.post('/api/editorial/validate')
    def validate_editorial(body: EditorialValidateRequest):
        return editorial_report(body)[1]

    @api.post('/api/editorial/use')
    def use_editorial(body: EditorialValidateRequest):
        source, report = editorial_report(body, force_images=True)
        # Cho phép chuyển bản đã sửa ngay cả khi còn cảnh báo/lỗi nhỏ; on_threads_build
        # sẽ báo lỗi cụ thể nếu cấu trúc không đọc được.
        state = copy.deepcopy(source)
        images = report['images']
        by_image = {item['image']: item for item in source.get('comments') or []}
        state['comments'] = [by_image[image] for image in images if image in by_image]
        file_map = {entry.get('rel'): entry for entry in source.get('images') or []}
        state['images'] = [file_map.get(image) or {'rel': image, 'path': str(pl.ILLUS_DIR / str(source.get('content') or '') / image)} for image in images]
        state['stats'] = {**(source.get('stats') or {}), 'comments_used': len(state['comments'])}
        settings_with({'content': state.get('content') or ''})
        built = actions.on_threads_build(body.cleaned, state)
        key = remember(state)
        return {**thread_result(state, body.cleaned, key), 'rows': built[1],
                'beats': decorate_rows(built[1], state.get('content') or ''), 'report': report,
                'note': 'Đã chuyển bản đã kiểm tra sang trình dựng. Nguồn trên đĩa được giữ nguyên.'}

    @api.post('/api/facebook/{action}')
    def facebook(action: str, body: FacebookRequest):
        if action == 'save':
            return {'message': actions.on_fb_save(body.page, body.token, body.version, body.tags)}
        if action == 'check':
            return jobs.submit('facebook-check', lambda _p: {'message': actions.on_fb_check(body.page, body.token, body.version)})
        if action == 'list':
            def listing(_progress):
                rows, _choices, note = actions.on_fb_list(body.page, body.token, body.version)
                return {'rows': rows, 'message': note}
            return jobs.submit('facebook-list', listing)
        if action == 'caption':
            if not body.source:
                raise HTTPException(400, 'Chọn bài Threads làm nguồn caption.')
            source = (APP_DIR / body.source).resolve()
            if pl.ILLUS_DIR.resolve() not in source.parents or source.name != 'threads.json' or not source.is_file():
                raise HTTPException(400, 'Nguồn caption không hợp lệ.')
            result = actions.on_fb_gen(str(source), body.tags, body.topic)
            return {'options': result[0]}
        if action in ('schedule', 'batch-plan', 'batch'):
            videos = body.videos if action != 'schedule' else [body.video]
            resolved = [media_path(v) for v in videos]
            if not resolved or any(p.suffix.lower() != '.mp4' or p.parent != pl.OUT_DIR.resolve() for p in resolved):
                raise HTTPException(400, 'Chọn video MP4 đã xuất trong output.')
            videos = list(map(str, resolved))
            if action == 'batch-plan':
                return {'rows': actions.on_fb_edit_rows(videos, body.pattern, body.edits or [], shared=body.caption if body.caption else None)['value']}
            if action == 'batch':
                return jobs.submit('facebook-batch', lambda progress: {'message': actions.on_fb_batch_schedule(
                    videos, body.pattern, body.caption, body.tags, body.edits, progress=progress)[0]})
            if not body.caption.strip():
                raise HTTPException(400, 'Hãy nhập caption trước khi đăng.')
            def schedule(progress):
                result = actions.on_fb_schedule(body.page, body.token, body.version, videos[0], '', body.caption,
                                                body.tags, body.when, body.now, progress=progress)
                return {'message': result[0], 'rows': result[1].get('value', [])}
            return jobs.submit('facebook-schedule', schedule)
        if action == 'cancel':
            if not body.post_id.strip():
                raise HTTPException(400, 'Chọn bài hẹn cần hủy.')
            return jobs.submit('facebook-cancel', lambda _p: {'message': actions.on_fb_cancel(
                body.page, body.token, body.version, body.post_id)[0]})
        raise HTTPException(404, 'Thao tác không tồn tại.')

    @api.post('/api/system/check')
    def system_check():
        return jobs.submit('system', lambda _p: {'message': actions.on_check()})

    dist = APP_DIR / 'frontend' / 'dist'
    if (dist / 'index.html').exists():
        api.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    else:
        @api.get('/')
        def not_built():
            return JSONResponse({'detail': 'Chưa build giao diện. Chạy npm ci rồi npm run build trong frontend/.'}, status_code=503)
    return api


def main():
    import uvicorn
    configure_browser_temp()
    port = int(os.environ.get('VIDEOMAKER_PORT', '7860'))
    if not os.environ.get('VIDEOMAKER_NO_BROWSER'):
        threading.Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{port}')).start()
    uvicorn.run(create_app(), host='127.0.0.1', port=port, log_level='info')
