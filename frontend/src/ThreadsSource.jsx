import React, { useEffect, useState } from 'react'
import { request } from './api'
import { Button, Field, Icon, Media, Notice } from './ui'

export default function ThreadsSource({ draft, work, notify, refresh, boot, revision, onRawThreads }) {
  const [url, setUrl] = useState('')
  const [sources, setSources] = useState([])
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState(() => ({ top: 20, mode: 'auto', ident: 'avatar', nested: true, reply_depth: 1, reply_min_likes: 10, reply_per_parent: 2, ...boot.settings.threads_scrape }))
  const [savingOptions, setSavingOptions] = useState(false)
  const [rawScript, setRawScript] = useState('')
  const rawText = draft.rawScript ?? rawScript
  useEffect(() => {
    const controller = new AbortController()
    request('/threads/sources', undefined, { signal: controller.signal }).then(data => setSources(data.items || [])).catch(error => { if (error.name !== 'AbortError') notify(error.message, 'error') })
    return () => controller.abort()
  }, [revision, notify])
  const accept = data => {
    setRawScript(data.raw_script ?? data.script ?? '')
    onRawThreads(data); refresh()
  }
  async function open() {
    setLoading(true)
    try { accept(await request('/threads/open', { path: source })) }
    catch (error) { notify(error.message, 'error') }
    finally { setLoading(false) }
  }
  async function copyScript() {
    if (!rawText) return
    try { await navigator.clipboard.writeText(rawText); notify('Đã sao chép bản thô.') }
    catch { notify('Không truy cập được clipboard. Hãy chọn và sao chép văn bản trong ô.', 'error') }
  }
  async function saveOptions() {
    setSavingOptions(true)
    try {
      const result = await request('/threads/options', config)
      setConfig(result.options)
      notify(result.message)
      refresh()
    } catch (error) { notify(error.message, 'error') }
    finally { setSavingOptions(false) }
  }
  return <div className="threads-source">
    <div className="source-head"><div><Icon name="threads" /><strong>Nguồn bài Threads</strong></div><Button variant="subtle" icon="link" disabled={work.busy} onClick={() => work.run('/threads/login', {}, result => { notify(result.message); refresh() })}>Đăng nhập</Button></div>
    <p className="muted small session-status">{boot.threads_status}</p>
    <div className="field-inline"><Field label="Link bài viết"><input type="url" value={url} placeholder="https://www.threads.com/@.../post/..." onChange={e => setUrl(e.target.value)} /></Field><Button variant="primary" icon="download" disabled={!url || work.busy || loading} onClick={() => work.run('/threads/scrape', { ...config, url, content: draft.content || '' }, accept)}>Lấy bài</Button></div>
    <details className="source-options"><summary>Tùy chọn lấy bài</summary><div className="three-fields">
      <Field label="Số comment"><input type="number" min="0" max="500" value={config.top} onChange={e => setConfig(c => ({ ...c, top: Number(e.target.value) }))} /></Field>
      <Field label="Ảnh bài"><select value={config.mode} onChange={e => setConfig(c => ({ ...c, mode: e.target.value }))}><option value="auto">Tự động</option><option value="shot">Ảnh chụp</option><option value="card">Card dựng lại</option></select></Field>
      <Field label="Danh tính"><select value={config.ident} onChange={e => setConfig(c => ({ ...c, ident: e.target.value }))}><option value="avatar">Avatar</option><option value="full">Avatar & tên</option><option value="no-avatar">Chỉ tên</option><option value="anon">Ẩn danh</option></select></Field>
      <Field label="Độ sâu reply"><input type="number" min="1" max="4" value={config.reply_depth} onChange={e => setConfig(c => ({ ...c, reply_depth: Number(e.target.value) }))} /></Field>
      <Field label="Like tối thiểu / reply"><input type="number" min="0" value={config.reply_min_likes} onChange={e => setConfig(c => ({ ...c, reply_min_likes: Number(e.target.value) }))} /></Field>
      <Field label="Reply mỗi comment"><input type="number" min="0" max="100" value={config.reply_per_parent} onChange={e => setConfig(c => ({ ...c, reply_per_parent: Number(e.target.value) }))} /></Field>
    </div><label className="checkbox-row"><input type="checkbox" checked={config.nested} onChange={e => setConfig(c => ({ ...c, nested: e.target.checked }))} /> Lấy reply lồng nhau</label>
      <Button icon="save" loading={savingOptions} disabled={work.busy} onClick={saveOptions}>Lưu tùy chọn</Button>
      <Button variant="subtle" disabled={work.busy} onClick={async () => { try { const result = await request('/threads/logout', {}); notify(result.message); refresh() } catch (error) { notify(error.message, 'error') } }}>Đăng xuất Threads</Button>
    </details>
    {sources.length ? <div className="saved-source field-inline"><Field label="Hoặc mở bài đã lưu"><select value={source} onChange={e => setSource(e.target.value)}><option value="">Chọn bài đã lấy…</option>{sources.map(item => <option key={item.path} value={item.path}>{item.label}</option>)}</select></Field><Button icon="folder" loading={loading} disabled={!source || work.busy} onClick={open}>Mở bài</Button></div> : null}
    {draft.session ? <>
      <div className="raw-script-card"><textarea className="script-input" aria-label="Bản thô" spellCheck={false} readOnly value={rawText} placeholder="Chưa có bản thô" /><div className="raw-script-actions"><Button icon="copy" variant="outline" disabled={!rawText} onClick={copyScript}>Sao chép</Button></div></div>
      {draft.images?.length ? <details className="comment-list"><summary>{draft.images.length} ảnh · {draft.comments.length} comment đã lấy</summary>
        <div className="comment-scroll">{draft.images.map((image, index) => <article className="comment-item" key={image.rel}><Media file={image} /><div><strong>{index === 0 ? 'Bài gốc' : draft.comments[index - 1]?.[3]}</strong><p>{index === 0 ? image.rel : draft.comments[index - 1]?.[5]}</p>{index > 0 ? <small>{draft.comments[index - 1]?.[4]} like · {draft.comments[index - 1]?.[6]}</small> : null}</div></article>)}</div>
      </details> : null}
    </> : null}
  </div>
}
