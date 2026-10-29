import React, { lazy, Suspense, useEffect, useState } from 'react'
import { download, request } from './api'
import { Button, Empty, Field, Icon, Modal, Notice } from './ui'

const Library = lazy(() => import('./Library'))

const KIND_LABEL = { post: 'Bài gốc', comment: 'Comment', reply: 'Reply' }

export default function LayoutPreview({ draft, settings, setSettings, save, threads, work, notify, refresh, revision, boot, onFrame, onClose }) {
  const chosen = draft.rows[draft.selected] || draft.rows[0]
  const [text, setText] = useState(chosen ? chosen[2] === '-' ? '' : String(chosen[2] || chosen[1]) : threads ? '' : 'Đây là *khung hình* xem thử.')
  const [clip, setClip] = useState(chosen?.[4] || draft.images?.[0]?.path || '')
  const [file, setFile] = useState(draft.frame || null)
  const [chunks, setChunks] = useState([])
  const [previewZoom, setPreviewZoom] = useState(false)
  const [picker, setPicker] = useState(false)
  const [items, setItems] = useState([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [selectedImage, setSelectedImage] = useState('')
  const [sources, setSources] = useState([])
  const [sourcePath, setSourcePath] = useState('')
  const [localSession, setLocalSession] = useState('')
  const session = draft.session || localSession
  const options = [
    ...(draft.images || []).map(image => ({ value: image.path, label: image.rel || image.name })),
    ...(draft.rows || []).filter(row => row[4]).map((row, index) => ({ value: row[4], label: `Nhịp ${index + 1} · ${row[4]}` })),
  ]
  const unique = [...new Map(options.map(option => [option.value, option])).values()]
  const selectedItem = items.find(item => item.image === selectedImage) || null

  useEffect(() => {
    if (!threads || !sourcePath || session) return undefined
    let active = true
    request('/threads/open', { path: sourcePath })
      .then(data => { if (active && data.session) setLocalSession(data.session) })
      .catch(error => { if (active) notify(error.message, 'error') })
    return () => { active = false }
  }, [threads, sourcePath, session, notify])

  useEffect(() => {
    if (!threads || !session) return undefined
    let active = true
    setItemsLoading(true)
    request(`/threads/preview-data?session=${encodeURIComponent(session)}`)
      .then(data => {
        if (!active) return
        const nextItems = data.items || []
        setItems(nextItems)
        setSelectedImage(previous => previous && nextItems.some(item => item.image === previous)
          ? previous
          : (nextItems[0]?.image || ''))
      })
      .catch(error => { if (active) notify(error.message, 'error') })
      .finally(() => { if (active) setItemsLoading(false) })
    return () => { active = false }
  }, [threads, session, revision, notify])

  useEffect(() => {
    if (!threads || session) return undefined
    let active = true
    request('/threads/sources')
      .then(data => { if (active) setSources(data.items || []) })
      .catch(error => { if (active) notify(error.message, 'error') })
    return () => { active = false }
  }, [threads, session, notify])

  async function generate() {
    if (threads) {
      try {
        const current = await request('/bootstrap')
        if (!Object.prototype.hasOwnProperty.call(current.defaults || {}, 'threads_zoom')) {
          notify('Backend đang chạy bản cũ nên chưa có chỉnh độ zoom. Hãy đóng cửa sổ chạy app, mở lại run.bat rồi tạo lại hình.', 'error')
          return
        }
      } catch (error) {
        notify(error.message, 'error')
        return
      }
      if (!session || !selectedImage) {
        notify('Cần chọn bài Threads đã scan bên dưới.', 'error')
        return
      }
      work.run('/threads/frame', {
        session,
        image: selectedImage,
        zoom: previewZoom,
        text: text.trim(),
        settings,
      }, result => {
        setFile(result.file); setChunks(result.chunks || []); onFrame?.(result.file)
        notify('Đã tạo 1 hình xem bố cục Threads. Không tạo giọng đọc hay xuất video.')
      })
      return
    }
    const context = chosen?.[4] === clip ? String(chosen?.[5] || '') : ''
    work.run('/frame', { settings, threads, session: draft.session,
      rows: [[1, 'Xem thử bố cục.', text.trim() || '-', '', clip, context]],
    }, result => {
      setFile(result.file); setChunks(result.chunks || []); onFrame?.(result.file)
      notify('Đã tạo 1 hình xem bố cục. Không tạo giọng đọc hay xuất video.')
    })
  }

  return <Modal title="Xem thử bố cục · 1 hình" wide onClose={onClose}>
    <div className="layout-preview-grid"><div className="layout-preview-controls">
      <p>Kiểm tra nền, vị trí ảnh, kiểu chữ và màu sắc bằng một khung hình thật. Có thể xem ngay cả khi chưa phân tích kịch bản.</p>
      <Field label="Chữ trên khung hình" hint="Để trống nếu không dùng phụ đề. Dấu * dùng để nhấn mạnh."><textarea rows={4} value={text} onChange={event => setText(event.target.value)} placeholder="Nhập một câu để thử bố cục chữ…" /></Field>
      {threads ? <>
        {!session && sources.length ? <Field label="Chọn bài đã scan">
          <select value={sourcePath} onChange={event => setSourcePath(event.target.value)}>
            <option value="">Chọn bài đã scan…</option>
            {sources.map(item => <option key={item.path} value={item.path}>{item.label}</option>)}
          </select>
        </Field> : null}
        {!session && !sources.length ? <Notice>Đang tải danh sách bài đã scan…</Notice> : null}
        {itemsLoading ? <Notice>Đang tải danh sách ảnh đã scan…</Notice> : null}
        {!itemsLoading && session && !items.length ? <Notice>Chưa có ảnh bài/comment/reply nào được scan.</Notice> : null}
        {items.length ? <Field label="Ảnh bài / comment / reply đã scan">
          <select value={selectedImage} onChange={event => setSelectedImage(event.target.value)}>
            {items.map(item => <option key={item.image} value={item.image}>
              {KIND_LABEL[item.kind] || item.kind}{item.handle ? ` · @${item.handle}` : ''}{item.text ? ` — ${String(item.text).slice(0, 48)}` : ''}
            </option>)}
          </select>
        </Field> : null}
        {selectedItem?.parent_snippet ? <Notice>↳ {selectedItem.parent_snippet}</Notice> : null}
        {selectedItem?.file ? <div className="layout-preview-summary"><span>Ảnh</span><strong>{selectedItem.image}</strong><span>Loại</span><strong>{KIND_LABEL[selectedItem.kind] || selectedItem.kind}</strong><span>Kích thước</span><strong>1080 × 1920</strong></div> : null}
        {setSettings ? <Field label={`Bo góc card Threads · ${settings.threads_radius || 0}px`}><input type="range" min="0" max="80" value={settings.threads_radius || 0} onChange={event => setSettings(old => ({ ...old, threads_radius: Number(event.target.value) }))} /></Field> : null}
        {setSettings ? <Field label={`Lề ngang card Threads · ${settings.threads_side_margin || 0}px`}><input type="range" min="0" max="120" value={settings.threads_side_margin || 0} onChange={event => setSettings(old => ({ ...old, threads_side_margin: Number(event.target.value) }))} /></Field> : null}
        {setSettings ? <fieldset><legend>Padding bên trong card (px)</legend>
          <p>Khoảng đệm giữa nội dung ảnh và mép card. Giữ nguyên kích thước khung.</p>
          {[['top', 'Trên'], ['right', 'Phải'], ['bottom', 'Dưới'], ['left', 'Trái']].map(([side, label]) => {
            const key = `threads_padding_${side}`
            const value = settings[key] >= 0 ? settings[key] : (settings.threads_padding || 0)
            return <Field key={side} label={label}><input type="number" min="0" max="200" step="1" value={value} onChange={event => setSettings(old => ({ ...old, [key]: Math.max(0, Math.min(200, Number(event.target.value))) }))} /></Field>
          })}
          <Button variant="outline" onClick={() => setSettings(old => ({ ...old, threads_padding: 0, threads_padding_top: 0, threads_padding_right: 0, threads_padding_bottom: 0, threads_padding_left: 0 }))}>Bỏ padding</Button>
        </fieldset> : null}
        {setSettings ? <Field label={`Độ zoom · ${settings.threads_zoom ?? 140}%`}><input type="range" min="100" max="200" step="5" value={settings.threads_zoom ?? 140} onChange={event => { setSettings(old => ({ ...old, threads_zoom: Number(event.target.value) })); setPreviewZoom(true) }} /></Field> : null}
        <label className="checkbox-row"><input type="checkbox" checked={previewZoom} onChange={event => setPreviewZoom(event.target.checked)} /> Xem nhịp phóng to</label>
        {setSettings ? <Field label={`Bóng đổ card Threads · ${settings.threads_shadow || 0}%`}><input type="range" min="0" max="100" value={settings.threads_shadow || 0} onChange={event => setSettings(old => ({ ...old, threads_shadow: Number(event.target.value) }))} /></Field> : null}
        <Notice>Chỉnh thông số rồi bấm tạo lại hình để xem thay đổi. Lưu bố cục để dùng cho lần sau và khi xuất video.</Notice>
      </> : <>
        <Field label="Ảnh / meme xem thử"><select value={clip} onChange={event => setClip(event.target.value)}><option value="">Chỉ xem nền và chữ</option>{clip && !unique.some(option => option.value === clip) ? <option value={clip}>{clip}</option> : null}{unique.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></Field>
        <Button icon="image" variant="outline" onClick={() => setPicker(true)}>Chọn ảnh/meme từ thư viện</Button>
        <div className="layout-preview-summary"><span>Nền</span><strong>{settings.bg}</strong><span>Chữ</span><strong>{settings.font_size}px · {settings.font}</strong><span>Kích thước</span><strong>1080 × 1920</strong></div>
      </>}
      {!threads ? null : <div className="layout-preview-summary"><span>Nền</span><strong>{settings.bg}</strong><span>Chữ</span><strong>{settings.font_size}px · {settings.font}</strong><span>Kích thước</span><strong>1080 × 1920</strong></div>}
      <Button variant="primary" icon="eye" disabled={work.busy || (threads ? !selectedImage : false)} loading={work.busy} onClick={generate}>Tạo 1 hình xem bố cục</Button>
      {work.busy ? <Notice>{work.job?.message || 'Đang xử lý…'}</Notice> : null}
      {chunks.length ? <Notice>{chunks.length} cụm chữ: {chunks.join(' · ')}. Ảnh hiển thị cụm đầu tiên.</Notice> : null}
    </div><div className="layout-preview-image">{file ? <a href={file.url} target="_blank" rel="noopener noreferrer" title="Mở ảnh kích thước đầy đủ"><img src={file.url} alt="Một khung hình xem thử bố cục video" /></a> : <Empty icon="image" title="Ảnh bố cục sẽ hiện tại đây">Bấm Tạo 1 hình để xem bố cục đang thiết lập.</Empty>}</div></div>
    <div className="modal-footer">{file ? <a href={download(file)} className="button" download><Icon name="download" size={16} /> Tải ảnh preview</a> : null}{save ? <Button icon="save" onClick={() => save()}>Lưu bố cục</Button> : null}<Button onClick={onClose}>Đóng</Button></div>
    {picker ? <Modal title="Chọn media để xem bố cục" wide onClose={() => setPicker(false)}><Suspense fallback={<p className="page-loading">Đang mở thư viện…</p>}><Library compact onPick={item => { setClip(item.path); setPicker(false) }} {...{ settings, notify, refresh, revision, boot }} /></Suspense></Modal> : null}
  </Modal>
}
