import React, { useEffect, useState } from 'react'
import { request } from './api'
import { Button, Empty, Field, Icon, Media, Modal, Notice } from './ui'

export default function Facebook({ boot, work, notify, refresh, revision, initialVideo }) {
  const [form, setForm] = useState({ ...boot.facebook, token: '', video: initialVideo?.path || '', caption: '', when: boot.facebook.suggested_time, now: false })
  const [tab, setTab] = useState('single')
  const [videos, setVideos] = useState([])
  const [sources, setSources] = useState([])
  const [source, setSource] = useState('')
  const [captionOptions, setCaptionOptions] = useState([])
  const [selected, setSelected] = useState([])
  const [edits, setEdits] = useState([])
  const [pattern, setPattern] = useState('2/ngày')
  const [scheduled, setScheduled] = useState([])
  const [confirmation, setConfirmation] = useState(null)
  const [pending, setPending] = useState(false)
  const [note, setNote] = useState('')
  const [connection, setConnection] = useState('')
  const set = (key, value) => setForm(old => ({ ...old, [key]: value }))
  useEffect(() => {
    const controller = new AbortController()
    Promise.all([request('/outputs', undefined, { signal: controller.signal }), request('/threads/sources', undefined, { signal: controller.signal })]).then(([output, source]) => { setVideos(output.items); setSources(source.items) }).catch(error => { if (error.name !== 'AbortError') notify(error.message, 'error') })
    return () => controller.abort()
  }, [revision, notify])
  useEffect(() => { if (initialVideo) setForm(old => ({ ...old, video: initialVideo.path })) }, [initialVideo])
  const video = videos.find(file => file.path === form.video)

  async function save() {
    setPending(true)
    try { const result = await request('/facebook/save', form); set('token', ''); setConnection(result.message); notify('Đã lưu cấu hình Facebook.'); refresh() }
    catch (error) { notify(error.message, 'error') }
    finally { setPending(false) }
  }
  async function suggest() {
    setPending(true)
    try { const result = await request('/facebook/caption', { ...form, source }); setCaptionOptions(result.options); set('caption', result.options[0]?.caption || '') }
    catch (error) { notify(error.message, 'error') }
    finally { setPending(false) }
  }
  async function plan() {
    setPending(true)
    try { const result = await request('/facebook/batch-plan', { ...form, videos: selected, pattern, edits: [] }); setEdits(result.rows); notify('Đã xếp giờ. Kiểm tra caption và giờ của từng video trước khi gửi.') }
    catch (error) { notify(error.message, 'error') }
    finally { setPending(false) }
  }
  function submit() {
    const action = confirmation
    setConfirmation(null)
    const body = { ...form, videos: selected, pattern, edits }
    if (action.startsWith('cancel:')) body.post_id = action.slice(7)
    work.run(`/facebook/${action.startsWith('cancel:') ? 'cancel' : action}`, body, result => {
      setNote(result.message); if (result.rows) setScheduled(result.rows)
      if (action === 'batch') { setSelected([]); setEdits([]) }
      refresh(); notify('Thao tác Facebook đã hoàn tất.')
    })
  }
  const tabs = [['single', 'Một video'], ['batch', 'Hẹn giờ hàng loạt'], ['scheduled', 'Bài đang chờ'], ['connection', 'Kết nối Page']]
  return <><section className="page-heading"><div><div className="eyebrow"><span /> PUBLISH & SCHEDULE</div><h1>Đưa câu chuyện đến người xem.</h1><p>Chuẩn bị caption, chọn thời điểm và đăng video lên Facebook Page.</p></div><span className={`connection-pill ${boot.facebook.configured ? 'connected' : ''}`}><span className="status-dot" />{boot.facebook.configured ? 'Đã có cấu hình Page' : 'Cần kết nối Page'}</span></section>
    <div className="page-tabs">{tabs.map(([id, title]) => <button className={tab === id ? 'active' : ''} key={id} onClick={() => setTab(id)}>{title}</button>)}</div>
    {tab === 'connection' ? <section className="panel form-panel"><h2>Kết nối Facebook Page</h2><Notice>{boot.facebook.note}</Notice><div className="two-fields"><Field label="Page ID"><input value={form.page} onChange={e => set('page', e.target.value)} placeholder="ID Facebook Page" autoComplete="off" /></Field><Field label="Phiên bản Graph API"><input value={form.version} onChange={e => set('version', e.target.value)} /></Field></div><Field label="Page access token" hint="Token đã lưu được giữ trên máy và không hiển thị lại."><input type="password" value={form.token} onChange={e => set('token', e.target.value)} placeholder="Để trống để dùng token đã lưu" autoComplete="new-password" /></Field><Field label="Hashtag mặc định"><input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="#chude #thongtin" /></Field><div className="form-actions"><Button icon="link" disabled={work.busy || pending} onClick={() => work.run('/facebook/check', form, result => setConnection(result.message))}>Kiểm tra kết nối</Button><Button variant="primary" icon="save" loading={pending} disabled={work.busy} onClick={save}>Lưu kết nối</Button></div><Notice>{connection}</Notice></section> : null}
    {tab === 'single' ? <div className="publish-grid"><section className="panel form-panel"><h2>Chuẩn bị Reel</h2><Field label="Video đã xuất"><select value={form.video} onChange={e => { set('video', e.target.value); setCaptionOptions([]) }}><option value="">Chọn một video…</option>{videos.map(file => <option key={file.path} value={file.path}>{file.name}{file.posted ? ' · đã đăng/hẹn' : ''}</option>)}</select></Field>
      <div className="field-inline"><Field label="Bài Threads làm nguồn caption"><select value={source} onChange={e => { setSource(e.target.value); setCaptionOptions([]) }}><option value="">Chọn bài nguồn (nếu có)…</option>{sources.map(item => <option key={item.path} value={item.path}>{item.label}</option>)}</select></Field><Button icon="layers" disabled={!source || pending || work.busy} onClick={suggest}>Gợi ý caption</Button></div>
      {captionOptions.length ? <div className="caption-options">{captionOptions.map((option, index) => <button key={option.title} className={form.caption === option.caption ? 'active' : ''} onClick={() => set('caption', option.caption)}>{index + 1}. {option.title}</button>)}</div> : null}
      <Field label="Caption"><textarea rows={8} value={form.caption} onChange={e => set('caption', e.target.value)} placeholder="Viết caption hoặc chọn bài nguồn để tạo gợi ý…" /></Field><Field label="Hashtag"><input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="#chude #thongtin" /></Field>
      <label className="checkbox-row"><input type="checkbox" checked={form.now} onChange={e => set('now', e.target.checked)} /> Đăng ngay sau khi tải lên</label>{!form.now ? <Field label="Ngày giờ đăng · giờ Việt Nam"><input value={form.when} onChange={e => set('when', e.target.value)} placeholder="ngày/tháng/năm giờ:phút" /><small>Ví dụ: 29/10/2026 20:00 · cách hiện tại ít nhất 15 phút.</small></Field> : null}
      {video?.posted ? <Notice>Video này đã được đăng hoặc hẹn giờ trước đó. Kiểm tra để tránh đăng trùng.</Notice> : null}
      <div className="form-actions"><Button variant="primary" icon={form.now ? 'facebook' : 'clock'} disabled={!form.video || !form.caption.trim() || (!form.now && !form.when) || work.busy} onClick={() => setConfirmation('schedule')}>{form.now ? 'Kiểm tra & đăng ngay' : 'Kiểm tra & lên lịch'}</Button></div>
    </section><aside className="panel publish-preview"><div className="panel-heading"><h2>Video đã chọn</h2><Icon name="facebook" /></div>{video ? <><Media file={video} controls /><strong>{video.name}</strong><p className="muted small">Caption và lịch đăng sẽ được kiểm tra trước khi gửi lên Page.</p></> : <Empty icon="film" title="Chọn video để bắt đầu">Các video đã xuất sẽ xuất hiện trong danh sách bên trái.</Empty>}</aside></div> : null}
    {tab === 'batch' ? <section className="panel form-panel batch-panel"><h2>Chọn video & xếp giờ</h2><p className="muted">Chọn danh sách, tạo lịch nháp rồi sửa giờ và caption riêng cho từng video.</p>{videos.length ? <div className="batch-video-list">{videos.map(file => <label key={file.path}><input type="checkbox" checked={selected.includes(file.path)} disabled={work.busy} onChange={e => { const checked = e.target.checked; setSelected(old => checked ? [...old, file.path] : old.filter(path => path !== file.path)); setEdits([]) }} /><span>{file.name}</span>{file.posted ? <small>Đã đăng / hẹn</small> : null}</label>)}</div> : <Empty title="Chưa có video để lên lịch">Xuất video trước khi chuẩn bị lịch đăng.</Empty>}
      <div className="two-fields"><Field label="Nhịp đăng"><select value={pattern} onChange={e => { setPattern(e.target.value); setEdits([]) }}><option value="2/ngày">2/ngày · 11:30 và 20:00</option><option value="1/ngày">1/ngày · 20:00</option></select></Field><Field label="Hashtag chung"><input value={form.tags} onChange={e => set('tags', e.target.value)} /></Field></div><Field label="Caption chung (tùy chọn)"><textarea rows={2} value={form.caption} onChange={e => set('caption', e.target.value)} placeholder="Để trống để tạo caption từ bài nguồn của từng video" /></Field><Button icon="clock" disabled={!selected.length || work.busy} loading={pending} onClick={plan}>Xếp giờ cho {selected.length} video</Button>
      {edits.length ? <><div className="batch-edits">{edits.map((row, index) => <article key={row[0]}><h3><span>{String(index + 1).padStart(2, '0')}</span>{row[0]}</h3><Field label="Giờ đăng"><input value={row[1]} onChange={e => setEdits(old => old.map((r, i) => i === index ? [r[0], e.target.value, r[2]] : r))} /></Field><Field label="Caption riêng"><textarea rows={3} value={row[2]} onChange={e => setEdits(old => old.map((r, i) => i === index ? [r[0], r[1], e.target.value] : r))} /></Field></article>)}</div><div className="form-actions"><Button variant="primary" icon="clock" disabled={work.busy || edits.some(row => !row[2]?.trim())} onClick={() => setConfirmation('batch')}>Kiểm tra & hẹn {edits.length} video</Button></div></> : null}
    </section> : null}
    {tab === 'scheduled' ? <section className="panel form-panel"><div className="section-title"><h2>Bài đang chờ đăng</h2><Button icon="refresh" disabled={work.busy} onClick={() => work.run('/facebook/list', form, result => { setScheduled(result.rows); setNote(result.message) })}>Tải danh sách từ Page</Button></div>{scheduled.length ? <div className="scheduled-list">{scheduled.map(row => <article key={row[0]}><div><strong>{row[1]}</strong><p>{row[2]}</p><small>ID: {row[0]}</small></div><Button variant="subtle danger" icon="trash" disabled={work.busy} onClick={() => setConfirmation(`cancel:${row[0]}`)}>Hủy lịch</Button></article>)}</div> : <Empty icon="clock" title="Danh sách lịch đăng">Bấm tải danh sách để đọc các bài đang được hẹn trên Facebook Page.</Empty>}</section> : null}
    {note ? <Notice>{note}</Notice> : null}
    {confirmation ? <Modal title={confirmation.startsWith('cancel:') ? 'Hủy lịch đăng?' : 'Xác nhận gửi lên Facebook'} onClose={() => setConfirmation(null)}><div className="confirmation-body">{confirmation.startsWith('cancel:') ? <p>Bài <strong>{confirmation.slice(7)}</strong> sẽ bị hủy lịch trên Page.</p> : confirmation === 'batch' ? <><p>Sẽ tải lên và hẹn <strong>{edits.length} video</strong> theo danh sách bạn vừa kiểm tra.</p><ul>{edits.map(row => <li key={row[0]}><strong>{row[0]}</strong><span>{row[1]}</span></li>)}</ul></> : <><p><strong>{video?.name}</strong></p><p>{form.now ? 'Đăng ngay sau khi Facebook xử lý xong.' : `Hẹn lúc ${form.when} (giờ Việt Nam).`}</p><blockquote>{form.caption}</blockquote><p>{form.tags}</p></>}</div><div className="modal-footer"><Button onClick={() => setConfirmation(null)}>Quay lại kiểm tra</Button><Button variant="primary" icon="check" disabled={work.busy} onClick={submit}>{confirmation.startsWith('cancel:') ? 'Xác nhận hủy lịch' : 'Xác nhận gửi'}</Button></div></Modal> : null}
  </>
}
