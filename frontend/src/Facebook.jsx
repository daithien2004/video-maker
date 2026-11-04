import React, { useEffect, useState } from 'react'
import { request } from './api'
import { Button, Empty, Field, Icon, Media, Modal, Notice } from './ui'

export default function Facebook({ boot, work, notify, refresh, revision, initialVideo }) {
  const [form, setForm] = useState({ ...boot.facebook, token: '', video: initialVideo?.path || '', caption: '', when: boot.facebook.suggested_time, now: false })
  const [tab, setTab] = useState('single')
  const [videos, setVideos] = useState([])
  const [captionSource, setCaptionSource] = useState('')
  const [scheduled, setScheduled] = useState([])
  const [confirmation, setConfirmation] = useState(null)
  const [pending, setPending] = useState(false)
  const [note, setNote] = useState('')
  const [connection, setConnection] = useState('')
  const set = (key, value) => setForm(old => ({ ...old, [key]: value }))
  useEffect(() => {
    const controller = new AbortController()
    request('/outputs', undefined, { signal: controller.signal }).then(output => setVideos(output.items)).catch(error => { if (error.name !== 'AbortError') notify(error.message, 'error') })
    return () => controller.abort()
  }, [revision, notify])
  useEffect(() => { if (initialVideo) setForm(old => ({ ...old, video: initialVideo.path })) }, [initialVideo])
  useEffect(() => {
    if (!form.video) { setCaptionSource(''); return }
    const controller = new AbortController()
    request('/facebook/caption', { video: form.video }, { signal: controller.signal }).then(result => {
      setCaptionSource(result.caption ? result.source : '')
      setForm(old => old.video === form.video ? { ...old, caption: result.caption } : old)
    }).catch(error => { if (error.name !== 'AbortError') notify(error.message, 'error') })
    return () => controller.abort()
  }, [form.video, notify])
  const video = videos.find(file => file.path === form.video)

  async function save() {
    setPending(true)
    try { const result = await request('/facebook/save', form); set('token', ''); setConnection(result.message); notify('Đã lưu cấu hình Facebook.'); refresh() }
    catch (error) { notify(error.message, 'error') }
    finally { setPending(false) }
  }
  function submit() {
    const action = confirmation
    setConfirmation(null)
    work.run(`/facebook/${action.startsWith('cancel:') ? 'cancel' : action}`, action.startsWith('cancel:') ? { ...form, post_id: action.slice(7) } : form, result => {
      setNote(result.message); if (result.rows) setScheduled(result.rows)
      refresh(); notify('Thao tác Facebook đã hoàn tất.')
    })
  }
  const tabs = [['single', 'Một video'], ['scheduled', 'Bài đang chờ'], ['connection', 'Kết nối Page']]
  return <><section className="page-heading"><div><div className="eyebrow"><span /> PUBLISH & SCHEDULE</div><h1>Đưa câu chuyện đến người xem.</h1><p>Chuẩn bị caption, chọn thời điểm và đăng video lên Facebook Page.</p></div><span className={`connection-pill ${boot.facebook.configured ? 'connected' : ''}`}><span className="status-dot" />{boot.facebook.configured ? 'Đã có cấu hình Page' : 'Cần kết nối Page'}</span></section>
    <div className="page-tabs">{tabs.map(([id, title]) => <button className={tab === id ? 'active' : ''} key={id} onClick={() => setTab(id)}>{title}</button>)}</div>
    {tab === 'connection' ? <section className="panel form-panel"><h2>Kết nối Facebook Page</h2><Notice>{boot.facebook.note}</Notice><div className="two-fields"><Field label="Page ID"><input value={form.page} onChange={e => set('page', e.target.value)} placeholder="ID Facebook Page" autoComplete="off" /></Field><Field label="Phiên bản Graph API"><input value={form.version} onChange={e => set('version', e.target.value)} /></Field></div><Field label="Page access token" hint="Token đã lưu được giữ trên máy và không hiển thị lại."><input type="password" value={form.token} onChange={e => set('token', e.target.value)} placeholder="Để trống để dùng token đã lưu" autoComplete="new-password" /></Field><Field label="Hashtag mặc định"><input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="#chude #thongtin" /></Field><div className="form-actions"><Button icon="link" disabled={work.busy || pending} onClick={() => work.run('/facebook/check', form, result => setConnection(result.message))}>Kiểm tra kết nối</Button><Button variant="primary" icon="save" loading={pending} disabled={work.busy} onClick={save}>Lưu kết nối</Button></div><Notice>{connection}</Notice></section> : null}
    {tab === 'single' ? <div className="publish-grid"><section className="panel form-panel"><h2>Chuẩn bị Reel</h2><Field label="Video đã xuất"><select value={form.video} onChange={e => set('video', e.target.value)}><option value="">Chọn một video…</option>{videos.map(file => <option key={file.path} value={file.path}>{file.name}{file.posted ? ' · đã đăng/hẹn' : ''}</option>)}</select></Field>
      <Field label="Caption" hint={captionSource ? `Soạn sẵn từ ${captionSource} — sửa lại nếu cần.` : undefined}><textarea rows={8} value={form.caption} onChange={e => set('caption', e.target.value)} placeholder="Chọn video để tự điền caption…" /></Field><Field label="Hashtag"><input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="#chude #thongtin" /></Field>
      <label className="checkbox-row"><input type="checkbox" checked={form.now} onChange={e => set('now', e.target.checked)} /> Đăng ngay sau khi tải lên</label>{!form.now ? <Field label="Ngày giờ đăng · giờ Việt Nam" hint="Mặc định 11:30 gần nhất. Ví dụ: 29/10/2026 11:30."><input value={form.when} onChange={e => set('when', e.target.value)} placeholder="ngày/tháng/năm giờ:phút" /></Field> : null}
      {video?.posted ? <Notice>Video này đã được đăng hoặc hẹn giờ trước đó. Kiểm tra để tránh đăng trùng.</Notice> : null}
      <div className="form-actions"><Button variant="primary" icon={form.now ? 'facebook' : 'clock'} disabled={!form.video || !form.caption.trim() || (!form.now && !form.when) || work.busy} onClick={() => setConfirmation('schedule')}>{form.now ? 'Kiểm tra & đăng ngay' : 'Kiểm tra & lên lịch'}</Button></div>
    </section><aside className="panel publish-preview"><div className="panel-heading"><h2>Video đã chọn</h2><Icon name="facebook" /></div>{video ? <><Media file={video} controls /><strong>{video.name}</strong><p className="muted small">Caption và lịch đăng sẽ được kiểm tra trước khi gửi lên Page.</p></> : <Empty icon="film" title="Chọn video để bắt đầu">Các video đã xuất sẽ xuất hiện trong danh sách bên trái.</Empty>}</aside></div> : null}
    {tab === 'scheduled' ? <section className="panel form-panel"><div className="section-title"><h2>Bài đang chờ đăng</h2><Button icon="refresh" disabled={work.busy} onClick={() => work.run('/facebook/list', form, result => { setScheduled(result.rows); setNote(result.message) })}>Tải danh sách từ Page</Button></div>{scheduled.length ? <div className="scheduled-list">{scheduled.map(row => <article key={row[0]}><div><strong>{row[1]}</strong><p>{row[2]}</p><small>ID: {row[0]}</small></div><Button variant="subtle danger" icon="trash" disabled={work.busy} onClick={() => setConfirmation(`cancel:${row[0]}`)}>Hủy lịch</Button></article>)}</div> : <Empty icon="clock" title="Danh sách lịch đăng">Bấm tải danh sách để đọc các bài đang được hẹn trên Facebook Page.</Empty>}</section> : null}
    {work.busy && work.job ? <Notice>Đang có tác vụ đang chạy: <strong>{work.job.message}</strong> — đợi tới khi có thông báo kết quả, chưa cần bấm lại.</Notice> : null}
    {note ? <Notice>{note}</Notice> : null}
    {confirmation ? <Modal title={confirmation.startsWith('cancel:') ? 'Hủy lịch đăng?' : 'Xác nhận gửi lên Facebook'} onClose={() => setConfirmation(null)}><div className="confirmation-body">{confirmation.startsWith('cancel:') ? <p>Bài <strong>{confirmation.slice(7)}</strong> sẽ bị hủy lịch trên Page.</p> : <><p><strong>{video?.name}</strong></p><p>{form.now ? 'Đăng ngay sau khi Facebook xử lý xong.' : `Hẹn lúc ${form.when} (giờ Việt Nam).`}</p><blockquote>{form.caption}</blockquote><p>{form.tags}</p></>}</div><div className="modal-footer"><Button onClick={() => setConfirmation(null)}>Quay lại kiểm tra</Button><Button variant="primary" icon="check" disabled={work.busy} onClick={submit}>{confirmation.startsWith('cancel:') ? 'Xác nhận hủy lịch' : 'Xác nhận gửi'}</Button></div></Modal> : null}
  </>
}
