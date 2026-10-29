import React, { useEffect, useState } from 'react'
import { date, download, request, size } from './api'
import { Button, Empty, Icon, Media, Modal } from './ui'

export default function Outputs({ revision, notify, onPublish, refresh, onDeleted }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [localRevision, setLocalRevision] = useState(0)
  const [selected, setSelected] = useState(null)
  const [removal, setRemoval] = useState(null)
  const [deleting, setDeleting] = useState(false)
  async function askRemove(file) {
    try {
      const plan = await request(`/outputs/related?path=${encodeURIComponent(file.path)}`)
      setSelected(null)
      setRemoval({ file, ...plan })
    } catch (error) { notify(error.message, 'error') }
  }
  async function remove() {
    setDeleting(true)
    try {
      const result = await request(`/outputs?path=${encodeURIComponent(removal.file.path)}`, undefined, { method: 'DELETE' })
      setItems(old => old.filter(item => item.path !== removal.file.path))
      onDeleted?.(removal.file)
      setRemoval(null)
      notify(result.message)
      refresh?.()
    } catch (error) { notify(error.message, 'error') }
    finally { setDeleting(false) }
  }
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    request('/outputs', undefined, { signal: controller.signal }).then(data => setItems(data.items)).catch(error => { if (error.name !== 'AbortError') setError(error.message) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [revision, localRevision])
  return <><section className="page-heading"><div><div className="eyebrow"><span /> YOUR COLLECTION</div><h1>Những câu chuyện đã thành hình.</h1><p>Video hoàn chỉnh, sẵn sàng để xem lại, tải về và chia sẻ.</p></div><Button icon="refresh" onClick={() => setLocalRevision(n => n + 1)} disabled={loading}>Quét lại video</Button></section>
    {loading ? <div className="page-loading"><span className="spinner" /> Đang đọc video…</div> : error ? <Empty title="Không đọc được video" action={<Button onClick={() => setLocalRevision(n => n + 1)}>Thử lại</Button>}>{error}</Empty> : items.length ? <div className="output-grid">{items.map(file => <article className="output-card" key={file.path}><button className="output-thumb" onClick={() => setSelected(file)} aria-label={`Xem ${file.name}`}><img className="output-poster" src={file.poster} alt="" loading="lazy" onError={event => { event.currentTarget.hidden = true }} /><span className="output-play"><Icon name="play" size={27} /></span><span className="media-kind">MP4 · 9:16</span></button><div className="output-info"><span className={`state-chip ${file.posted ? 'posted' : ''}`}><span />{file.posted ? 'Đã đăng / hẹn giờ' : 'Sẵn sàng sử dụng'}</span><h3 title={file.name}>{file.name}</h3><p>{date(file.modified)} <i /> {size(file.size)}</p><div className="output-actions"><a href={download(file)} className="button" download><Icon name="download" size={16} /> Tải video</a><Button variant="subtle" icon="facebook" onClick={() => onPublish(file)}>Đăng Reel</Button><Button variant="danger" icon="trash" disabled={deleting} onClick={() => askRemove(file)}>Xóa</Button></div></div></article>)}</div> : <Empty icon="film" title="Chưa có video hoàn chỉnh">Xuất video từ trình dựng để lưu thành phẩm tại đây.</Empty>}
    {selected ? <Modal title={selected.name} onClose={() => setSelected(null)}><div className="output-modal-preview"><Media file={selected} controls autoPlay /></div><div className="modal-footer"><a className="button primary" href={download(selected)} download><Icon name="download" size={16} /> Tải video</a><Button onClick={() => { onPublish(selected); setSelected(null) }} icon="facebook">Chuẩn bị đăng Reel</Button></div></Modal> : null}
    {removal ? <Modal title="Xóa video đã xuất?" onClose={() => { if (!deleting) setRemoval(null) }}>
      <div className="output-delete">
        <div className="output-delete-file">
          <span className="output-delete-symbol"><Icon name="trash" size={20} /></span>
          <div><strong>{removal.file.name}</strong><span>{date(removal.file.modified)} · {size(removal.file.size)}</span></div>
        </div>
        <p className="muted small">{removal.files.length} file sẽ bị xóa vĩnh viễn khỏi thư mục <code>output/</code>:</p>
        <ul className="output-delete-list">{removal.files.map(path => <li key={path}><Icon name={path.endsWith('.mp4') ? 'film' : 'save'} size={16} /><span title={path}>{path.replace(/^output\//, '')}</span></li>)}</ul>
        <p className="muted small">Thư mục dựng tạm trong <code>work/</code> và các video khác được giữ nguyên.</p>
      </div>
      <div className="modal-footer"><Button disabled={deleting} onClick={() => setRemoval(null)}>Hủy</Button><Button variant="danger" icon="trash" loading={deleting} onClick={remove}>Xóa video và file đi kèm</Button></div>
    </Modal> : null}
  </>
}
