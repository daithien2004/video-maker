import React, { lazy, Suspense, useMemo, useRef, useState } from 'react'
import { download, request } from './api'
import { Button, Card, Empty, Field, Icon, Media, Modal, Notice } from './ui'
import ThreadsSource from './ThreadsSource'
import { mapSourceLines, prepareScriptDraft, sourceIsPrepared, renderRows } from './script-preparation'
import Voice, { voiceLines, voiceReady, voiceSignature } from './Voice'

const Library = lazy(() => import('./Library'))
const LayoutPreview = lazy(() => import('./LayoutPreview'))

// Nhịp zoom tự sinh không nằm trong kịch bản, nên xoá nó phải ghi dấu vào dòng '#'
// của mục để lần "Tạo nhịp và voice" sau không thêm lại.
function markNoZoom(script, clip) {
  const lines = script.split(/\r?\n/)
  const index = lines.findIndex(line => {
    const body = line.trim()
    return body.startsWith('#') && body.replace(/^#+/, '').trim().split(/\s+/)[0] === clip
  })
  if (index < 0 || /\[nozoom\]/i.test(lines[index])) return script
  const at = lines[index].indexOf(clip) + clip.length
  lines[index] = `${lines[index].slice(0, at)} [nozoom]${lines[index].slice(at)}`
  return lines.join(script.includes('\r\n') ? '\r\n' : '\n')
}

export default function Editor({ mode, draft, update, settings, setSettings, save, boot, work, notify, refresh, revision, onRawThreads }) {
  const threads = mode === 'threads'
  const [tab, setTab] = useState(!threads && draft.rows.length ? 'beats' : 'script')
  const [analyzing, setAnalyzing] = useState(false)
  const [picker, setPicker] = useState(null)
  const [showFrame, setShowFrame] = useState(Boolean(draft.frame && !draft.output))
  const [expandedBeats, setExpandedBeats] = useState(new Set())
  const [layoutPreview, setLayoutPreview] = useState(false)
  const uploadRef = useRef()
  const cfg = { ...settings, content: draft.content ?? settings.content }
  const words = useMemo(() => (draft.script.match(/\S+/g) || []).length, [draft.script])
  const chosen = draft.rows[draft.selected] || draft.rows[0]
  const mediaCount = draft.rows.filter(row => row[4]).length
  const lines = voiceLines(draft.voiceRows || [], threads)
  const voiceItems = new Map((draft.voice || []).map(item => [item.beat, item]))
  const voiceDone = lines.filter(line => voiceReady(line, voiceItems.get(line.beat), voiceSignature(cfg))).length
  const sourceReady = sourceIsPrepared(draft, cfg.content)
  const allVoicesReady = sourceReady && lines.length > 0 && voiceDone === lines.length
  // Cột 7 là công tắc zoom; hàng 6 cột của phiên cũ vẫn đọc `[zoom]` trong lời đọc.
  const zoomOn = row => Boolean(row) && (row.length > 6 ? row[6] === '1' : row[1] === '[zoom]')
  const body = () => ({ script: draft.script, rows: draft.rows, settings: cfg, threads, session: draft.session })
  const setScript = script => update(current => ({ ...current, script, frame: null, output: null }))
  const voiceBody = () => ({ ...body(), script: draft.preparedScript, rows: draft.voiceRows || [] })

  async function saveThreadScript() {
    try {
      const result = await request('/threads/save-script', { session: draft.session, script: draft.script })
      notify(result.message)
      refresh()
    } catch (error) { notify(error.message, 'error') }
  }

  async function analyze() {
    setAnalyzing(true)
    try {
      const source = body()
      const data = await request('/analyze', source)
      const signature = voiceSignature(source.settings)
      update(current => prepareScriptDraft(current, data, source.script, source.settings.content, threads))
      setTab('voice')
      work.run('/voice', { ...source, rows: data.rows, session: data.session || source.session }, result => {
        update(current => current.preparedScript === source.script && current.preparedContent === (data.content ?? source.settings.content)
          ? { ...current, voice: result.items.map(item => ({ ...item, signature })) } : current)
        notify(result.message)
      })
    } catch (error) { notify(error.message, 'error') }
    finally { setAnalyzing(false) }
  }
  function edit(index, column, value) {
    update(current => ({ ...current, frame: null, rows: current.rows.map((row, i) => i === index ? row.map((v, j) => j === column ? value : v) : row) }))
  }
  function attach(file) {
    update(current => ({ ...current, frame: null, rows: current.rows.map((row, i) => i === picker ? row.map((v, j) => j === 4 ? file.path : v) : row), beats: current.rows.map((row, i) => ({ row, media: i === picker ? file : current.beats[i]?.media })) }))
    setPicker(null)
  }
  function toggleZoom(index) {
    update(current => ({ ...current, frame: null, rows: current.rows.map((row, i) => {
      if (i !== index) return row
      const next = row.slice(0, 7)
      while (next.length < 7) next.push('')
      next[6] = zoomOn(row) ? '' : '1'
      return next
    }) }))
  }
  function dropZoomBeat(index) {
    update(current => {
      const row = current.rows[index]
      if (!threads || !row || row[1] !== '[zoom]' || current.sourceLines?.[index] != null) return current
      const script = row[4] ? markNoZoom(current.script, row[4]) : current.script
      const cut = (list = []) => list.filter((_, i) => i !== index).map((item, i) => (Array.isArray(item) ? [i + 1, ...item.slice(1)] : item))
      const rows = cut(current.rows)
      const voiceRows = cut(current.voiceRows || [])
      const beats = current.beats.filter((_, i) => i !== index)
      const voice = (current.voice || [])
        .filter(item => item.beat !== index + 1)
        .map(item => item.beat > index + 1 ? { ...item, beat: item.beat - 1 } : item)
      return {
        ...current, script, rows, voiceRows, beats, voice, preparedScript: script,
        sourceLines: mapSourceLines(script, rows, threads),
        selected: Math.max(0, Math.min(current.selected || 0, rows.length - 1)), frame: null, output: null,
      }
    })
  }
  async function readScript(event) {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > 1024 * 1024) { notify('Kịch bản tối đa 1 MB.', 'error'); return }
    try { setScript((await file.text()).replace(/^\uFEFF/, '')); notify(`Đã mở ${file.name}.`) }
    catch (error) { notify(error.message, 'error') }
    event.target.value = ''
  }
  function exportScript() {
    const script = draft.script
    const url = URL.createObjectURL(new Blob([script], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = `${cfg.content || 'kich-ban'}.txt`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  function render(preview) {
    if (!allVoicesReady) { setTab('voice'); return }
    work.run('/render', { ...body(), rows: renderRows(draft), preview }, result => { update({ output: result.file }); setShowFrame(false); notify(result.message); refresh() })
  }
  function frame() {
    work.run('/frame', { ...body(), rows: [chosen] }, result => { update({ frame: result.file }); setShowFrame(true) })
  }
  const displayed = showFrame && draft.frame ? draft.frame : draft.output

  return <>
    <section className="page-heading"><div><div className="eyebrow"><span /> {threads ? 'THREADS → VIDEO' : 'VIDEO WORKSPACE'}</div><h1>{threads ? 'Một cuộc trò chuyện. Một video.' : 'Biến kịch bản thành câu chuyện.'}</h1><p>{threads ? 'Lấy bài viết, chỉnh lời đọc và dựng video từ những cuộc trò chuyện.' : 'Chuẩn bị kịch bản và media, chỉnh từng nhịp rồi xem thành quả của bạn.'}</p></div></section>
    <div className="editor-top-actions"><Button icon="eye" variant="primary" onClick={() => setLayoutPreview(true)}>Xem thử bố cục · 1 hình</Button></div>
    <div className="workspace-grid">
      <div className="editor-column">
        <div className="workflow"><div className={`workflow-step ${tab === 'script' ? 'current' : 'done'}`}><span>{draft.rows.length ? <Icon name="check" size={14} /> : '01'}</span><button onClick={() => setTab('script')}>Chuẩn bị kịch bản</button></div><div className="step-line" /><div className={`workflow-step ${tab === 'beats' ? 'current' : ''}`}><span>02</span><button onClick={() => setTab('beats')}>Chỉnh các nhịp</button></div><div className="step-line" /><div className={`workflow-step ${draft.output ? 'done' : ''}`}><span>{draft.output ? <Icon name="check" size={14} /> : '03'}</span><button onClick={() => setTab('voice')}>Voice</button></div></div>
        <div className="content-title-row"><Field label="Tên nội dung" hint="Tên này nối kịch bản với thư viện ảnh cùng chủ đề."><input value={cfg.content} disabled={analyzing || work.busy} placeholder="Ví dụ: su-that-ve-mat-troi" onChange={e => update({ content: e.target.value, rows: [], beats: [], frame: null })} list="contents" /><datalist id="contents">{boot.contents.map(c => <option key={c} value={c} />)}</datalist></Field><span className="format-badge">9:16 <i /> VIDEO DỌC</span></div>
        {threads ? <ThreadsSource {...{ draft, update, work, notify, refresh, boot, revision, onRawThreads }} /> : null}
        {!sourceReady && draft.rows.length > 0 ? <Notice>Kịch bản đã thay đổi. Bấm “Tạo nhịp và voice” ở tab Kịch bản để đồng bộ trước khi xuất. Có thể sửa từng lời đọc ở tab Voice; thêm/xóa hoặc đổi thứ tự tại Kịch bản.</Notice> : null}
        <Card className="panel script-panel">
          <div className="panel-heading"><div className="panel-tabs"><button className={tab === 'script' ? 'selected' : ''} onClick={() => setTab('script')}><Icon name="film" size={16} /> Kịch bản</button><button className={tab === 'beats' ? 'selected' : ''} onClick={() => setTab('beats')}><Icon name="layers" size={16} /> Các nhịp <span>{draft.rows.length.toString().padStart(2, '0')}</span></button><button className={tab === 'voice' ? 'selected' : ''} onClick={() => setTab('voice')}><Icon name="audio" size={16} /> Voice <span>{voiceDone}/{lines.length}</span></button></div><button className="icon-button" aria-label="Tải kịch bản" title="Tải kịch bản" onClick={exportScript} disabled={!draft.script}><Icon name="download" size={18} /></button></div>
          {tab === 'voice' ? <div className="voice-panel"><Voice {...{ draft, update, work, notify, threads }} body={voiceBody} settings={cfg} sourceReady={sourceReady} /></div> : tab === 'script' ? <>
            <div className="script-toolbar"><span><span className="status-dot" /> {threads ? 'BẢN CHỈNH' : 'KỊCH BẢN'}</span>{threads ? <Button icon="save" variant="subtle" disabled={!draft.session || work.busy} onClick={saveThreadScript}>Lưu kịch bản</Button> : null}{!threads ? <><Button icon="save" variant="subtle" onClick={() => save('script')}>Lưu kịch bản</Button><Button icon="upload" variant="subtle" onClick={() => uploadRef.current.click()}>Mở file .txt</Button><input ref={uploadRef} type="file" accept=".txt,.md" hidden onChange={readScript} /></> : null}</div>
            <textarea className="script-input" spellCheck={false} aria-label="Kịch bản video" value={draft.script} disabled={analyzing || work.busy} onChange={e => setScript(e.target.value)} placeholder={threads ? 'Dán hoặc chỉnh kịch bản tại đây…' : '# Mỗi dòng là một nhịp đọc\n[mat-troi] Ánh sáng cần khoảng tám phút để đến Trái Đất. || ÁNH SÁNG CẦN KHOẢNG *8 PHÚT* ĐỂ ĐẾN TRÁI ĐẤT.\n\nDán kịch bản đã chuẩn bị vào đây…'} />
            <div className="script-meta"><span>{words.toLocaleString('vi-VN')} từ <i /> {draft.script.split('\n').filter(line => line.trim() && !line.trim().startsWith('#')).length} dòng đọc</span><span>UTF-8 <i /> Tiếng Việt</span></div>
          </> : draft.rows.length ? <div className="beats-list">{draft.rows.map((row, index) => {
            const open = expandedBeats.has(index)
            return <article key={index} className={`beat-card ${draft.selected === index ? 'chosen' : ''} ${open ? 'open' : ''}`}>
              <div className="beat-heading" onClick={() => setExpandedBeats(prev => {
                const next = new Set(prev)
                if (next.has(index)) next.delete(index)
                else next.add(index)
                return next
              })}>
                <button className="beat-select" onClick={e => { e.stopPropagation(); update({ selected: index }) }}><span>{String(index + 1).padStart(2, '0')}</span>NHỊP ĐỌC</button>
                <div className="beat-actions">{threads ? <button className={`beat-zoom${zoomOn(row) ? ' on' : ''}`} aria-pressed={zoomOn(row)} disabled={!row[4]} title={!row[4] ? 'Chọn media trước khi bật zoom' : zoomOn(row) ? 'Đang zoom · bấm để tắt' : 'Bật zoom (ẩn phụ đề)'} onClick={e => { e.stopPropagation(); toggleZoom(index) }}>Zoom</button> : null}{threads && row[1] === '[zoom]' && draft.sourceLines && draft.sourceLines[index] == null ? <button className="beat-drop" aria-label={`Xoá nhịp zoom tự động ${index + 1}`} title="Xoá nhịp zoom tự động" disabled={work.busy} onClick={e => { e.stopPropagation(); dropZoomBeat(index) }}><Icon name="trash" size={13} /></button> : null}</div>
                {open ? <span className="collapse-hint">Ấn để thu gọn</span> : null}
              </div>
              {open ? <>
                <div className="beat-fields"><div><Field label="Lời đọc · sửa ngay trong tab Voice"><textarea rows={2} value={row[1]} readOnly /></Field><Field label={threads && zoomOn(row) ? 'Chữ hiển thị · zoom đang ẩn phụ đề' : 'Chữ hiển thị · nhập dấu - để tắt'}><textarea rows={2} value={row[2]} onChange={e => edit(index, 2, e.target.value)} /></Field></div><button className="beat-media" onClick={e => { e.stopPropagation(); setPicker(index) }} aria-label={`Chọn media nhịp ${index + 1}`}>{draft.beats[index]?.media ? <Media file={draft.beats[index].media} /> : <Icon name="image" size={24} />}<span>{row[4] ? 'Đổi media' : 'Chọn media'}</span></button></div>
                <div className="beat-bottom"><Field label="Thẻ"><input value={row[3]} onChange={e => edit(index, 3, e.target.value)} placeholder="ten-the" /></Field><Field label="File media"><input value={row[4]} title={row[4]} onChange={e => { edit(index, 4, e.target.value); update(current => ({ ...current, beats: current.beats.map((beat, i) => i === index ? { ...beat, media: null } : beat) })) }} placeholder="Chọn từ thư viện hoặc nhập đường dẫn" /></Field><button className="icon-button" title="Bỏ media" aria-label={`Bỏ media nhịp ${index + 1}`} onClick={e => { e.stopPropagation(); edit(index, 4, ''); update(current => ({ ...current, beats: current.beats.map((beat, i) => i === index ? { ...beat, media: null } : beat) })) }}><Icon name="close" size={15} /></button></div>
                {threads && row[5] ? <p className="parent-context">↳ {row[5]}</p> : null}
              </> : null}
            </article>
          })}</div> : <Empty icon="layers" title="Chưa có nhịp">Bấm “Tạo nhịp và voice” ở tab Kịch bản để chuẩn bị cả hai.</Empty>}
          <div className="editor-actionbar">{tab === 'script' ? <><p><Icon name="info" size={15} />Tạo cả nhịp và voice từ kịch bản này. Lời không đổi sẽ dùng lại voice đã có.</p><Button variant="primary" icon="audio" loading={analyzing || work.busy} disabled={!draft.script.trim() || work.busy || analyzing} onClick={analyze}>Tạo nhịp và voice</Button></> : tab === 'beats' ? <><p><Icon name="info" size={15} />Chỉnh hình, chữ và zoom không đổi voice. Sửa từng lời đọc ở tab Voice; thêm/xóa hoặc đổi thứ tự tại Kịch bản.</p><Button variant="primary" icon="arrow" disabled={!lines.length || work.busy} onClick={() => setTab('voice')}>Nghe và kiểm tra voice</Button></> : <><p><Icon name="info" size={15} />Nghe và tạo lại đoạn sai. Tạo lại voice không đổi các nhịp.</p><Button variant="primary" icon="export" disabled={!allVoicesReady || work.busy} onClick={() => render(false)}>Xuất video đẹp</Button></>}</div>
        </Card>
        {!threads ? draft.note ? <Notice>{draft.note}</Notice> : <div className="workflow-hint"><Icon name="library" size={20} /><div><strong>Media đã sẵn sàng?</strong><p>Thẻ trong kịch bản sẽ tự tìm ảnh đúng chủ đề và meme trong thư viện.</p></div></div> : null}
      </div>
      <aside className="preview-column"><Card className="panel preview-panel"><div className="panel-heading"><h2><span className="status-dot" /> Xem trước</h2><span className="tiny-label">9:16</span></div><div className="preview-stage"><div className="phone-frame">{displayed ? <Media file={displayed} controls key={displayed.url} /> : <div className="preview-empty"><div className="viewfinder"><Icon name="play" size={26} /></div><strong>Khung hình chờ câu chuyện</strong><p>Bản xem thử sẽ xuất hiện<br />tại đây khi bạn dựng video.</p><span>1080 × 1920</span></div>}<span className="phone-corner top-left" /><span className="phone-corner bottom-right" /></div></div>
        {draft.frame && draft.output ? <div className="preview-toggle"><button className={showFrame ? 'selected' : ''} onClick={() => setShowFrame(true)}>Khung hình</button><button className={!showFrame ? 'selected' : ''} onClick={() => setShowFrame(false)}>Video</button></div> : null}
        <div className="preview-info"><div><span>Các nhịp</span><strong>{draft.rows.length.toString().padStart(2, '0')}</strong></div><div><span>Có media</span><strong>{mediaCount.toString().padStart(2, '0')}<small> / {draft.rows.length}</small></strong></div><div><span>Giọng đọc</span><strong className="voice-label">{settings.backend === 'dummy' ? 'Thử' : 'VieNeu'}</strong></div></div>
        <div className="preview-buttons"><Button icon="eye" onClick={frame} disabled={!chosen || work.busy}>Xem khung nhịp {(draft.selected || 0) + 1}</Button><Button icon="play" variant="primary" disabled={!allVoicesReady || work.busy} onClick={() => render(true)}>Dựng bản xem thử</Button><Button icon="export" variant="outline" disabled={!allVoicesReady || work.busy} onClick={() => render(false)}>Xuất video đẹp</Button>{draft.output ? <a className="text-link" href={download(draft.output)} download><Icon name="download" size={15} /> Tải {draft.output.name}</a> : null}</div>
      </Card><div className="preview-note"><Icon name="info" size={16} /><p>Tạo nhịp và voice từ tab Kịch bản. Kiểm tra hình và voice độc lập, rồi Xuất video đẹp khi đã ổn.</p></div></aside>
    </div>
    {layoutPreview ? <Suspense fallback={<p className="page-loading">Đang mở xem bố cục…</p>}><LayoutPreview {...{ draft, settings: cfg, setSettings, threads, work, notify, refresh, revision, boot }} save={() => save(threads ? 'threads-layout' : 'video-layout')} onFrame={file => { update({ frame: file }); setShowFrame(true) }} onClose={() => setLayoutPreview(false)} /></Suspense> : null}
    {picker !== null ? <Modal title={`Chọn media cho nhịp ${picker + 1}`} wide onClose={() => setPicker(null)}><Suspense fallback={<p>Đang mở thư viện…</p>}><Library compact onPick={attach} {...{ notify, refresh, revision, settings: cfg, boot }} /></Suspense></Modal> : null}
  </>
}
