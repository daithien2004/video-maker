import React, { useEffect, useMemo, useRef, useState } from 'react'
import { download, request, size } from './api'
import { Button, Empty, Field, Icon, Media, Modal } from './ui'

const TYPES = { all: 'Tất cả', illus: 'Minh họa', meme: 'Meme', bg: 'Video nền', music: 'Nhạc', font: 'Font' }

export default function Library({ compact = false, onPick, notify, refresh, revision, settings }) {
  const [items, setItems] = useState([])
  const [kind, setKind] = useState('all')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [upload, setUpload] = useState(false)
  const [preview, setPreview] = useState(null)
  const [limit, setLimit] = useState(24)
  const [localRevision, setLocalRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    request('/library', undefined, { signal: controller.signal }).then(data => setItems(data.items)).catch(error => { if (error.name !== 'AbortError') setError(error.message) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [revision, localRevision])
  const filtered = useMemo(() => items.filter(item => (kind === 'all' || item.kind === kind) && (!onPick || ['meme', 'illus', 'bg'].includes(item.kind)) && `${item.name} ${item.tag}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi'))), [items, kind, query, onPick])
  async function remove(file) {
    if (!window.confirm(`Xóa “${file.name}” khỏi thư viện? Kịch bản đang dùng file này có thể cần chọn lại media.`)) return
    try { const result = await request(`/library?path=${encodeURIComponent(file.path)}`, undefined, { method: 'DELETE' }); notify(result.message); setItems(old => old.filter(item => item.path !== file.path)); refresh() }
    catch (error) { notify(error.message, 'error') }
  }
  return <div className={compact ? 'library-compact' : ''}>
    {!compact ? <section className="page-heading"><div><div className="eyebrow"><span /> MEDIA LIBRARY</div><h1>Mọi chất liệu cho câu chuyện.</h1><p>Minh họa theo chủ đề, meme theo cảm xúc. Chọn đúng hình cho từng nhịp.</p></div><Button variant="primary" icon="plus" onClick={() => setUpload(true)}>Thêm media</Button></section> : null}
    <div className="library-toolbar"><div className="filter-tabs">{Object.entries(TYPES).filter(([key]) => !onPick || ['all', 'illus', 'meme', 'bg'].includes(key)).map(([key, label]) => <button className={kind === key ? 'active' : ''} key={key} onClick={() => { setKind(key); setLimit(24) }}>{label}{!compact ? <small>{key === 'all' ? items.length : items.filter(item => item.kind === key).length}</small> : null}</button>)}</div><div className="search-input"><Icon name="search" size={17} /><input aria-label="Tìm media" placeholder="Tìm tên, chủ đề, thẻ…" value={query} onChange={e => { setQuery(e.target.value); setLimit(24) }} /></div></div>
    {loading ? <div className="page-loading"><span className="spinner" /> Đang đọc thư viện…</div> : error ? <Empty title="Chưa mở được thư viện" action={<Button onClick={() => setLocalRevision(n => n + 1)} icon="refresh">Thử lại</Button>}>{error}</Empty> : filtered.length ? <><div className="media-grid">{filtered.slice(0, limit).map(item => <article className="media-card" key={item.path}><button className="media-thumb" onClick={() => onPick ? onPick(item) : setPreview(item)} aria-label={onPick ? `Dùng ${item.name}` : `Xem ${item.name}`}>{item.poster ? <img className="thumb-poster" src={item.poster} alt="" loading="lazy" /> : <Media file={item} />}<span className="media-kind">{TYPES[item.kind]}</span><div className="media-hover"><Icon name={onPick ? 'plus' : 'eye'} /><span>{onPick ? 'Dùng media này' : 'Xem media'}</span></div></button><div className="media-card-info"><strong title={item.name}>{item.name}</strong><div><span title={item.tag}>{item.tag === '.' ? 'Dùng chung' : item.tag}</span><small>{size(item.size)}</small>{!onPick ? <button className="icon-button danger" aria-label={`Xóa ${item.name}`} onClick={() => remove(item)}><Icon name="trash" size={14} /></button> : null}</div></div></article>)}</div>{filtered.length > limit ? <div className="load-more"><Button onClick={() => setLimit(n => n + 24)}>Xem thêm {Math.min(24, filtered.length - limit)} file</Button></div> : null}</> : <Empty icon="library" title={query ? 'Không tìm thấy media phù hợp' : 'Thư mục này đang chờ media'}>{query ? 'Thử từ khóa khác hoặc chọn một loại media khác.' : 'Thêm ảnh, video, nhạc hoặc font để bắt đầu.'}</Empty>}
    {upload ? <Upload settings={settings} onClose={() => setUpload(false)} onDone={() => { setUpload(false); setLocalRevision(n => n + 1); refresh() }} notify={notify} /> : null}
    {preview ? <Modal title={preview.name} onClose={() => setPreview(null)}><div className="media-modal-preview"><Media file={preview} controls /></div><div className="modal-footer"><a className="button" href={download(preview)} download><Icon name="download" size={16} /> Tải file</a><Button onClick={() => setPreview(null)}>Đóng</Button></div></Modal> : null}
  </div>
}

function Upload({ settings, onClose, onDone, notify }) {
  const [kind, setKind] = useState('illus')
  const [content, setContent] = useState(settings.content || '')
  const [tag, setTag] = useState('')
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const ref = useRef()
  async function submit(event) {
    event.preventDefault()
    if (!files.length || uploading) return
    const data = new FormData(); data.append('kind', kind); data.append('content', content); data.append('tag', tag)
    files.forEach(file => data.append('files', file))
    setUploading(true)
    try { const result = await request('/library/upload', data); notify(result.message); onDone() }
    catch (error) { notify(error.message, 'error') }
    finally { setUploading(false) }
  }
  const accept = { illus: 'image/*,video/*,.gif', meme: 'image/*,video/*,.gif', bg: 'video/*,.gif', music: 'audio/*', font: '.ttf,.otf,.ttc' }[kind]
  return <Modal title="Thêm media vào thư viện" onClose={() => { if (!uploading) onClose() }}><form onSubmit={submit}>
    <div className="upload-form"><Field label="Loại media"><select value={kind} onChange={e => { setKind(e.target.value); setFiles([]); if (ref.current) ref.current.value = '' }}>{Object.entries(TYPES).filter(([key]) => key !== 'all').map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
      {kind === 'illus' ? <Field label="Tên nội dung"><input required value={content} onChange={e => setContent(e.target.value)} placeholder="ten-chu-de" /></Field> : null}
      {kind === 'illus' || kind === 'meme' ? <Field label={kind === 'meme' ? 'Thẻ cảm xúc' : 'Thẻ chủ thể / cảnh'}><input required value={tag} onChange={e => setTag(e.target.value)} placeholder={kind === 'meme' ? 'soc, cuoi, batluc…' : 'mat-troi, trai-dat…'} /></Field> : null}
      <label className="dropzone"><Icon name="upload" size={30} /><strong>{files.length ? `Đã chọn ${files.length} file` : 'Chọn ảnh hoặc file media'}</strong><span>Mỗi file tối đa 1 GB · lưu trực tiếp trên máy</span><input ref={ref} type="file" accept={accept} multiple onChange={e => setFiles(Array.from(e.target.files))} /></label>{files.length ? <ul className="upload-files">{files.map(file => <li key={`${file.name}-${file.size}`}>{file.name}<span>{size(file.size)}</span></li>)}</ul> : null}
    </div><div className="modal-footer"><Button type="button" disabled={uploading} onClick={onClose}>Hủy</Button><Button type="submit" variant="primary" icon="upload" loading={uploading} disabled={!files.length}>Thêm vào thư viện</Button></div>
  </form></Modal>
}
