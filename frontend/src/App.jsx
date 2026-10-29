import React, { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { request } from './api'
import { useJob } from './useJob'
import { Badge, Button, Icon, Notice } from './ui'
import { useTheme } from './useTheme'
import { receiveRawThread } from './threads-flow'
import Editor from './Editor'
import Inspector from './Inspector'

const Library = lazy(() => import('./Library'))
const Outputs = lazy(() => import('./Outputs'))
const Facebook = lazy(() => import('./Facebook'))
const System = lazy(() => import('./System'))

const NAV = [
  ['video', 'film', 'Video thường'], ['threads', 'threads', 'Threads'],
  ['library', 'library', 'Thư viện media'], ['outputs', 'layers', 'Video đã xuất'],
  ['facebook', 'facebook', 'Facebook Reels'],
]
const TITLES = { video: 'Video thường', threads: 'Threads', library: 'Thư viện media', outputs: 'Video đã xuất', facebook: 'Facebook Reels', system: 'Kiểm tra hệ thống' }
const newDraft = (script, content = '') => ({ script, content, rawScript: '', rawSession: '', approved: false, rows: [], beats: [], note: '', session: '', images: [], comments: [], output: null, frame: null, selected: 0 })

export default function App() {
  const { theme, toggleTheme } = useTheme()
  const [page, setPage] = useState('threads')
  const [visited, setVisited] = useState(() => new Set())
  const navigate = (id) => {
    setPage(id)
    if (!['video', 'threads'].includes(id)) setVisited(old => old.has(id) ? old : new Set([...old, id]))
  }
  const [boot, setBoot] = useState(null)
  const [bootError, setBootError] = useState('')
  const [settings, setSettings] = useState(null)
  const [voiceCatalog, setVoiceCatalog] = useState({})
  const [drafts, setDrafts] = useState({ video: newDraft(''), threads: newDraft('') })
  const [toast, setToast] = useState(null)
  const [revision, setRevision] = useState(0)
  const [saving, setSaving] = useState(false)
  const [inspector, setInspector] = useState(false)
  const [publishVideo, setPublishVideo] = useState(null)
  const toastTimer = useRef()
  const notify = useCallback((text, tone = 'success') => {
    setToast({ text, tone }); clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), tone === 'error' ? 10000 : 5000)
  }, [])
  useEffect(() => () => clearTimeout(toastTimer.current), [])

  const refresh = useCallback(() => {
    setRevision(n => n + 1)
    request('/bootstrap').then(setBoot).catch(error => notify(error.message, 'error'))
  }, [notify])
  const initial = useCallback(async () => {
    setBootError('')
    try {
      const data = await request('/bootstrap')
      setBoot(data); setSettings(data.settings)
      setDrafts({ video: newDraft(data.settings.script || '', data.settings.content), threads: newDraft('') })
    } catch (error) { setBootError(error.message) }
  }, [])
  useEffect(() => { initial() }, [initial])

  const updateDraft = useCallback((mode, update) => {
    setDrafts(current => ({ ...current, [mode]: typeof update === 'function' ? update(current[mode]) : { ...current[mode], ...update } }))
  }, [])
  const completed = useCallback(job => {
    if (job.result?.file) {
      const mode = job.result.threads ? 'threads' : 'video'
      if (job.kind === 'frame') updateDraft(mode, { frame: job.result.file })
      else if (['preview', 'export'].includes(job.kind)) updateDraft(mode, { output: job.result.file })
    }
    notify(job.result?.message || 'Tác vụ đã hoàn tất.'); refresh()
  }, [notify, refresh, updateDraft])
  const work = useJob(notify, completed)

  async function save(scope = 'settings') {
    if (saving) return false
    setSaving(true)
    try {
      const current = await request('/bootstrap')
      const script = scope === 'script' ? drafts.video.script : current.settings.script
      const updates = scope === 'script'
        ? { content: drafts.video.content }
        : Object.fromEntries(Object.entries(settings).filter(([key]) =>
          scope === 'threads-layout' ? key.startsWith('threads_') && key !== 'threads_scrape'
            : scope === 'video-layout' ? ['meme_y', 'meme_w', 'meme_h', 'bg', 'font', 'font_size', 'text_color', 'outline_color', 'outline_w', 'text_y', 'emph_color', 'emph_scale', 'max_words', 'pop', 'upper'].includes(key)
              : key !== 'content' && key !== 'script' && !key.startsWith('threads_')))
      await request('/settings', { script, settings: updates })
      notify(scope === 'script' ? 'Đã lưu kịch bản Video thường.' : scope.endsWith('layout') ? 'Đã lưu bố cục.' : 'Đã lưu thiết lập chung.')
      return true
    } catch (error) { notify(error.message, 'error'); return false }
    finally { setSaving(false) }
  }

  if (!boot || !settings) return <div className="startup"><div className="brand-mark"><Icon name="film" size={27} /></div><h1>VideoMaker<span>Studio</span></h1>{bootError ? <><Notice tone="error">{bootError}</Notice><Button onClick={initial} icon="refresh">Kết nối lại</Button></> : <p><span className="spinner" /> Đang mở không gian làm việc…</p>}</div>

  const common = { settings, setSettings, voiceCatalog, setVoiceCatalog, save, boot, work, notify, refresh, revision,
    onRawThreads: data => {
      updateDraft('threads', current => receiveRawThread(current, data))
    } }
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" aria-label="VideoMaker Studio" onClick={e => { e.preventDefault(); navigate('threads') }}><span className="brand-mark"><Icon name="film" size={25} /></span><span>VideoMaker<small>CREATOR STUDIO</small></span></a>
      <div className="sidebar-label">KHÔNG GIAN LÀM VIỆC</div>
      <nav aria-label="Điều hướng chính">{NAV.map(([id, icon, title]) => <button key={id} aria-label={title} title={title} aria-current={page === id ? 'page' : undefined} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => navigate(id)}><Icon name={icon} /><span>{title}</span>{id === 'outputs' && boot.counts.videos > 0 ? <small>{boot.counts.videos}</small> : null}</button>)}</nav>
      <div className="sidebar-project"><span className="mini-eyebrow">THƯ VIỆN CỦA BẠN</span><strong>{boot.counts.memes} <span>meme sẵn sàng</span></strong><p>Ảnh theo chủ đề. Meme dùng chung. Mọi thứ ở cùng một nơi.</p><button onClick={() => navigate('library')}>Mở thư viện <Icon name="arrow" size={15} /></button></div>
      <div className="sidebar-bottom"><button aria-label="Kiểm tra hệ thống" title="Kiểm tra hệ thống" className={`nav-item ${page === 'system' ? 'active' : ''}`} onClick={() => navigate('system')}><Icon name="monitor" /><span>Kiểm tra hệ thống</span></button><div className="local-status"><span className="status-dot" /><span>Đang chạy trên máy bạn</span><Icon name="link" size={13} /></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><span>Không gian làm việc</span><Icon name="chevron" size={14} /><strong>{TITLES[page]}</strong></div><div className="top-actions"><Badge variant="outline" className="local-badge"><span className="status-dot" /> LOCAL STUDIO</Badge><Button variant="subtle" className="theme-toggle" icon={theme === 'light' ? 'moon' : 'sun'} aria-label={`Chuyển giao diện ${theme === 'light' ? 'tối' : 'sáng'}`} title={`Chuyển giao diện ${theme === 'light' ? 'tối' : 'sáng'}`} onClick={toggleTheme} /><Button icon="settings" variant="subtle" onClick={() => setInspector(true)}>Thiết lập chung</Button></div></header>
      <main>
        {work.busy ? <div className="job-bar" role="status" aria-live="polite"><span className="spinner" /><div><strong>{work.job.message}</strong><div className="progress-track"><span style={{ width: `${Math.max(3, (work.job.progress || 0) * 100)}%` }} /></div></div><span>{Math.round((work.job.progress || 0) * 100)}%</span></div> : null}
        {page === 'video' || page === 'threads' ? <Editor key={page} mode={page} draft={drafts[page]} update={update => updateDraft(page, update)} {...common} /> : null}
        {['library', 'outputs', 'facebook', 'system'].map(id => visited.has(id) ? <section key={id} hidden={page !== id} aria-label={TITLES[id]}><Suspense fallback={<div className="page-loading"><span className="spinner" /> Đang mở…</div>}>
          {id === 'library' ? <Library {...common} /> : null}
          {id === 'outputs' ? <Outputs {...common} onDeleted={file => {
            setDrafts(current => Object.fromEntries(Object.entries(current).map(([key, draft]) => [key, draft.output?.path === file.path ? { ...draft, output: null } : draft])))
            setPublishVideo(current => current?.path === file.path ? null : current)
          }} onPublish={file => { setPublishVideo(file); navigate('facebook') }} /> : null}
          {id === 'facebook' ? <Facebook {...common} initialVideo={publishVideo} /> : null}
          {id === 'system' ? <System {...common} /> : null}
        </Suspense></section> : null)}
      </main>
      <footer className="footer"><span>VideoMaker Studio</span><span>Kịch bản của bạn. Câu chuyện của bạn.</span><span>1080 × 1920 <i /> {settings.fps || 60} FPS</span></footer>
    </div>
    {inspector ? <Inspector {...{ settings, setSettings, voiceCatalog, setVoiceCatalog, boot, work, notify }} threads={false} onClose={() => setInspector(false)} onApply={async () => { if (await save() !== false) setInspector(false) }} /> : null}
    {toast ? <div className={`toast ${toast.tone}`} role={toast.tone === 'error' ? 'alert' : 'status'}><Icon name={toast.tone === 'error' ? 'info' : 'check'} /><span>{toast.text}</span><button className="icon-button" aria-label="Đóng thông báo" onClick={() => setToast(null)}><Icon name="close" size={16} /></button></div> : null}
  </div>
}
