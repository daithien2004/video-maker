import React, { useEffect, useRef, useState } from 'react'
import { date, request } from './api'
import { Badge, Button, Card, Empty, Field, Icon, Modal, Notice, Switch } from './ui'
import { curatePrompt, downloadText, normalizePrompt } from './editorial-prompts'

const STAGES = [
  { title: 'Prepare', by: 'Code xử lý', detail: 'Dựng cây cha–con, sắp thứ tự', field: 'raw_script', file: 'source.txt', label: 'Kịch bản thô nhận từ Threads' },
  { title: 'Done', by: 'Bạn sửa', detail: 'Bản đã sửa để dựng video', field: 'cleaned', file: 'tts-cleaned.txt', label: 'Bản đã sửa để dựng video' },
]
const EMPTY = { session: '', source_text: '', raw_script: '', prepared_script: '', curated: '', cleaned: '', seed: '', tree: [], counts: {}, warnings: [], content: '' }

export default function Editorial({ notify, initialSource, onUse, onBack, onResume, boot }) {
  const backendReady = (boot?.api_revision || 0) >= 3
  const [draft, setDraft] = useState(EMPTY)
  const [stage, setStage] = useState(0)
  const [report, setReport] = useState(null)
  const [checkImages, setCheckImages] = useState(true)
  const [pending, setPending] = useState(false)
  const [prompt, setPrompt] = useState(null)
  const [history, setHistory] = useState([])
  const [historySelection, setHistorySelection] = useState('')
  const [saveStatus, setSaveStatus] = useState('')
  const [savedAt, setSavedAt] = useState(null)
  const [restoredReport, setRestoredReport] = useState(false)
  const generation = useRef(0)
  const resumedInput = useRef(null)
  const incoming = useRef(initialSource)
  incoming.current = initialSource
  const latestDraft = useRef(draft)
  latestDraft.current = draft
  const saveQueue = useRef(Promise.resolve())
  const refs = { raw_script: useRef(), curated: useRef(), cleaned: useRef() }

  useEffect(() => {
    if (!backendReady) return
    if (resumedInput.current?.session === initialSource?.session && resumedInput.current?.script === initialSource?.script) {
      resumedInput.current = null
      return
    }
    if (initialSource?.session && initialSource.script?.trim()) prepare({ session: initialSource.session, script: initialSource.script, prefer_saved: true })
    else { generation.current += 1; setDraft(EMPTY); setReport(null); setStage(0); setPending(false) }
  }, [initialSource, backendReady])

  useEffect(() => {
    if (!backendReady) return
    let cancelled = false
    request('/editorial/history').then(data => {
      if (cancelled) return
      setHistory(data.items)
      if (!incoming.current?.session && !latestDraft.current.session) {
        const recent = data.items.find(item => item.kind === 'workspace')
        if (recent) restore(recent)
      }
    }).catch(error => { if (!cancelled) notify(error.message, 'error') })
    return () => { cancelled = true }
  }, [backendReady])

  const snapshot = draft.session ? { session: draft.session, draft: {
    raw_script: draft.raw_script, prepared_script: draft.prepared_script, source_text: draft.source_text,
    curated: draft.curated, cleaned: draft.cleaned, stage, check_images: checkImages, report, client_revision: Date.now(),
  } } : null
  const latestSnapshot = useRef(snapshot)
  latestSnapshot.current = snapshot

  useEffect(() => {
    if (!snapshot || pending || !backendReady) return
    setSaveStatus('dirty')
    const timer = setTimeout(() => save(snapshot), 800)
    return () => clearTimeout(timer)
  }, [draft, stage, checkImages, report, pending, backendReady])

  useEffect(() => {
    if (!backendReady) return
    function flush() {
      if (!latestSnapshot.current) return
      navigator.sendBeacon('/api/editorial/save', new Blob([JSON.stringify(latestSnapshot.current)], { type: 'application/json' }))
    }
    window.addEventListener('pagehide', flush)
    return () => window.removeEventListener('pagehide', flush)
  }, [backendReady])

  async function refreshHistory() {
    try { const result = await request('/editorial/history'); setHistory(result.items) }
    catch (error) { notify(error.message, 'error') }
  }

  function save(value = latestSnapshot.current) {
    if (!value) return Promise.resolve()
    setSaveStatus('saving')
    const revision = generation.current
    const task = saveQueue.current.catch(() => {}).then(() => request('/editorial/save', value))
    saveQueue.current = task
    return task.then(result => {
      if (revision === generation.current && value.draft.raw_script === latestDraft.current.raw_script && value.draft.curated === latestDraft.current.curated && value.draft.cleaned === latestDraft.current.cleaned) { setSaveStatus('saved'); setSavedAt(result.updated) }
      return result
    }).catch(error => { setSaveStatus('error'); notify('Chưa lưu được phiên biên tập: ' + error.message, 'error') })
  }

  async function restore(item) {
    await saveQueue.current.catch(() => {})
    if (latestSnapshot.current && !await save(latestSnapshot.current)) return
    const revision = ++generation.current
    setPending(true)
    try {
      const result = await request('/editorial/restore', { id: item.id, kind: item.kind })
      if (revision !== generation.current) return
      const saved = result.saved || {}
      setDraft({ ...EMPTY, ...result, ...saved, session: result.session,
        raw_script: saved.raw_script ?? result.seed, prepared_script: saved.prepared_script ?? result.seed })
      setStage(Math.min(saved.stage ?? 0, 1)); setCheckImages(saved.check_images ?? true)
      setReport(saved.report || null); setRestoredReport(!!saved.report)
      setSavedAt(result.updated); setSaveStatus(result.updated ? 'saved' : 'dirty')
      resumedInput.current = result.origin
      onResume(result.origin)
      setHistorySelection(`${item.kind}:${item.id}`)
      notify(item.kind === 'workspace' ? 'Đã khôi phục các bước đang làm. Không scan lại.' : 'Đã mở bài đã scan và tạo bản thô từ dữ liệu có sẵn.')
    } catch (error) { notify(error.message, 'error') }
    finally { if (revision === generation.current) setPending(false) }
  }

  async function prepare(body, nextStage = 0) {
    const current = ++generation.current
    setPending(true)
    try {
      if (latestSnapshot.current && !await save(latestSnapshot.current)) return
      const result = await request('/editorial/prepare', body)
      if (generation.current !== current) return
      const saved = result.saved || {}
      setDraft({ ...EMPTY, ...result, ...saved, session: result.session,
        raw_script: saved.raw_script ?? result.seed, prepared_script: saved.prepared_script ?? result.seed })
      setReport(saved.report || null); setRestoredReport(!!saved.report); setStage(Math.min(saved.stage ?? nextStage, 1))
      setCheckImages(saved.check_images ?? true)
      setSavedAt(result.updated || null)
      notify(result.saved ? 'Đã mở lại đúng phiên biên tập đã lưu của bài này.' : 'Đã dựng nguồn cha–con. Chưa tuyển chọn hay sửa lời đọc.')
    } catch (error) { if (generation.current === current) notify(error.message, 'error') }
    finally { if (generation.current === current) setPending(false) }
  }
  function change(field, value) {
    generation.current += 1
    setDraft(old => (field === 'cleaned'
      ? { ...old, cleaned: value, curated: value }
      : { ...old, [field]: value })); setReport(null)
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); notify('Đã sao chép. Bạn có thể dán sang LLM bên ngoài.') }
    catch { notify('Không truy cập được clipboard. Hãy chọn và sao chép văn bản trong ô.', 'error') }
  }
  async function validate() {
    const current = generation.current
    setPending(true)
    try {
      const result = await request('/editorial/validate', { session: draft.session, curated: draft.curated, cleaned: draft.cleaned, check_images: checkImages })
      if (generation.current === current) { setReport(result); setRestoredReport(false); setStage(1) }
    } catch (error) { notify(error.message, 'error') }
    finally { setPending(false) }
  }
  async function useInEditor() {
    setPending(true)
    try {
      if (!await save()) return
      const result = await request('/editorial/use', { session: draft.session, curated: draft.curated, cleaned: draft.cleaned, check_images: true })
      onUse(result); notify('Đã chuyển bản đã kiểm tra sang trình dựng Threads. Chưa render video.')
    } catch (error) { notify(error.message, 'error') }
    finally { setPending(false) }
  }
  function jump(issue) {
    const field = issue.stage === 'curated' ? 'curated' : issue.stage === 'cleaned' ? 'cleaned' : 'raw_script'
    setStage(field === 'curated' ? 1 : field === 'cleaned' ? 2 : 0)
    requestAnimationFrame(() => {
      const input = refs[field].current
      if (!input) return
      const lines = input.value.split('\n'), index = Math.max(0, (issue.line || 1) - 1)
      const start = lines.slice(0, index).reduce((sum, line) => sum + line.length + 1, 0)
      input.focus(); input.setSelectionRange(start, start + (lines[index]?.length || 0))
      input.scrollTop = Math.max(0, index - 2) * parseFloat(getComputedStyle(input).lineHeight)
    })
  }
  const current = STAGES[stage]
  const text = current.field ? draft[current.field] : ''
  const populated = [!!draft.session, !!draft.cleaned.trim()]
  const rawChanged = draft.raw_script !== draft.prepared_script

  if (!backendReady) return <section className="panel form-panel"><h1>Cần khởi động lại app</h1><Notice>Giao diện đã cập nhật, nhưng máy chủ Python vẫn chạy bản cũ nên chưa có chức năng Biên tập Threads.</Notice><ol className="restart-instructions"><li>Đóng cửa sổ terminal đang chạy app (hoặc bấm Ctrl+C trong cửa sổ đó).</li><li>Mở lại run.bat trong thư mục VideoMaker.</li><li>Tải lại trang và mở Biên tập Threads.</li></ol><p className="muted small">F5 chỉ tải lại giao diện, không khởi động lại máy chủ Python. Bài đã scan và các phiên đã lưu trên máy vẫn được giữ.</p><Button icon="threads" onClick={onBack}>Về tab Threads</Button></section>

  return <>
    <section className="page-heading"><div><div className="eyebrow"><span /> THREADS EDITORIAL</div><h1>Từ hội thoại đến lời đọc.</h1><p>Code chuẩn bị và kiểm tra. Bạn tự tuyển chọn, chuẩn hóa bằng LLM bên ngoài rồi dán kết quả về đây.</p></div><Badge variant="outline" className="editorial-manual">Không gọi LLM trong app</Badge></section>
    <Card className="panel editorial-history"><div className="editorial-history-controls"><Field label="Tiếp tục bài đã scan"><select value={historySelection} disabled={pending} onFocus={refreshHistory} onChange={event => setHistorySelection(event.target.value)}><option value="">Chọn bài để tiếp tục, không scan lại…</option>{history.map(item => <option key={`${item.kind}:${item.id}`} value={`${item.kind}:${item.id}`}>{item.label} · {date(item.updated)} · {item.kind === 'workspace' ? `đang ở ${STAGES[item.stage || 0].title}` : 'đã có ảnh và bản thô'}</option>)}</select></Field><Button icon="folder" disabled={pending || !historySelection} onClick={() => { const item = history.find(item => `${item.kind}:${item.id}` === historySelection); if (item) restore(item) }}>Mở để tiếp tục</Button><Button icon="save" variant="outline" disabled={!draft.session || pending || saveStatus === 'saving'} onClick={() => save().then(result => { if (result) { notify('Đã lưu toàn bộ các bước của phiên này.'); refreshHistory() } })}>Lưu phiên</Button></div><div className={`editorial-save-status ${saveStatus === 'error' ? 'error' : ''}`} role="status">{draft.session ? <><Icon name={saveStatus === 'saved' ? 'check' : saveStatus === 'error' ? 'info' : 'clock'} size={15} /><span>{saveStatus === 'saved' ? `Đã tự lưu${savedAt ? ` · ${date(savedAt)}` : ''}` : saveStatus === 'saving' ? 'Đang lưu các bước…' : saveStatus === 'error' ? 'Chưa lưu được. Giữ trang mở và thử Lưu phiên lại.' : 'Có thay đổi, sắp tự lưu…'}</span></> : <span>Các bài đã scan trước đây cũng mở được từ danh sách này. Phiên đang làm sẽ tự lưu trên máy.</span>}</div></Card>
    <Card className="panel editorial-source"><div className="editorial-handoff"><Icon name="threads" size={25} /><div><strong>{initialSource?.session ? `Đã nhận kịch bản thô${draft.content || initialSource.content ? ` · ${draft.content || initialSource.content}` : ''}` : 'Bắt đầu từ tab Threads'}</strong><p>{initialSource?.session ? 'Bài và ảnh đã lấy xong. Xử lý kịch bản tại đây; chỉ chuyển bản hoàn chỉnh về Threads khi kiểm tra đạt.' : 'Dán link bài trong Threads, lấy bài và chụp ảnh. Kịch bản thô sẽ được đưa thẳng vào tab Biên tập.'}</p></div><Button variant="outline" icon="threads" onClick={onBack}>Về tab Threads</Button></div>{pending && !draft.session ? <p className="editorial-loading"><span className="spinner" /> Đang nhận bản thô và sắp cây cha–con…</p> : null}</Card>
    <div className="editorial-steps" aria-label="Các bước biên tập">{STAGES.map((step, index) => <button key={step.title} className={`editorial-step ${stage === index ? 'active' : ''}`} disabled={pending || (index > 0 && (!draft.session || rawChanged))} onClick={() => setStage(index)} aria-current={stage === index ? 'step' : undefined}><span className={`editorial-step-number ${populated[index] ? 'complete' : ''}`}>{populated[index] ? <Icon name="check" size={16} /> : index + 1}</span><span><strong>{step.title}</strong><small>{step.by}</small><p>{step.detail}</p></span></button>)}</div>
    <div className="editorial-workspace"><div className="editorial-main">
      {stage < 3 ? <Card className="panel editorial-editor"><div className="panel-heading"><h2>{stage + 1}. {current.label}</h2><Badge variant="secondary">Ô text chỉnh sửa được</Badge></div>
        {!draft.session ? <Empty icon="threads" title={pending ? 'Đang khôi phục phiên…' : 'Mở bài đã scan hoặc lấy bài mới'} action={!pending ? <Button icon="threads" variant="primary" onClick={onBack}>Về Threads để lấy bài mới</Button> : null}>Chọn bài đã scan ở danh sách phía trên để làm tiếp bản thô và các bước đã lưu. Chỉ cần lấy bài mới khi chưa có dữ liệu.</Empty> : <><p className="editorial-guidance">{stage === 0 ? 'Đây là kịch bản thô từ bài vừa lấy, đã sắp cha trước con. Xem xong bấm Prepare, rồi dán bản bạn đã sửa ở bước Done.' : 'Dán bản bạn đã sửa hoàn chỉnh. Mỗi ảnh bắt đầu bằng # ten-anh.png, bên dưới là lời đọc; dùng || - nếu không phụ đề.'}</p>
          <div className="editorial-toolbar"><div><Button icon="link" variant="subtle" disabled={!text} onClick={() => copy(text)}>Sao chép text</Button><Button icon="download" variant="subtle" disabled={!text} onClick={() => downloadText(current.file, text)}>Tải .txt</Button></div>{stage > 0 ? <Button icon="plus" variant="outline" disabled={pending} onClick={() => change(current.field, draft.raw_script)}>Bắt đầu từ bản thô</Button> : null}</div>
          <Field className="editorial-text-field" label={current.label}><textarea ref={refs[current.field]} rows={18} spellCheck={false} disabled={pending} value={text} onChange={event => change(current.field, event.target.value)} placeholder={stage === 0 ? 'Nguồn cha–con sẽ hiển thị ở đây…' : '# post/ten-anh.png\nLời đọc của mục || -'} /></Field>
          <div className="editorial-editor-footer"><span>{text.length.toLocaleString('vi-VN')} ký tự · {current.file}</span>{stage < 1 ? <Button icon="arrow" variant="primary" loading={pending} disabled={pending || !text.trim()} onClick={() => prepare({ session: initialSource.session, script: draft.raw_script }, 1)}>{'Prepare & sang Done'}</Button> : <Button icon="check" variant="primary" loading={pending} disabled={!draft.cleaned.trim()} onClick={useInEditor}>OK · chuyển về Threads</Button>}</div>
        </>}
      </Card> : <Card className="panel editorial-validation"><div className="panel-heading"><h2>4. Kết quả kiểm tra</h2><Button icon="refresh" disabled={!draft.session || !draft.curated.trim() || !draft.cleaned.trim()} loading={pending} onClick={validate}>Kiểm tra lại</Button></div><div className="editorial-report-body">{restoredReport ? <Notice>K?t qu? l?n tr??c ???c gi? l?i. B?m Ki?m tra l?i ?? x?c nh?n ?nh v? b?n th?o hi?n t?i tr??c khi chuy?n sang tr?nh d?ng.</Notice> : null}<label className="switch-row" htmlFor="check-editorial-images"><span>Kiểm tra file ảnh trong thư viện trên máy</span><Switch id="check-editorial-images" checked={checkImages} disabled={pending} onCheckedChange={value => { setCheckImages(value); setReport(null) }} /></label>
        {!report ? <Empty icon="check" title="Chưa có kết quả cho bản hiện tại">Hoàn thành hai ô curated và tts-cleaned rồi bấm kiểm tra. Mỗi lần sửa văn bản cần kiểm tra lại.</Empty> : <><div className={`validation-status ${report.status}`} role="status"><Icon name={report.status === 'passed' ? 'check' : 'info'} size={23} /><div><h3>{report.status === 'error' ? 'Chưa đạt — cần sửa lỗi' : report.status === 'review' ? 'Đạt cấu trúc — còn phần cần rà' : 'Đạt các kiểm tra bằng code'}</h3><p>{report.errors.length} lỗi · {report.warnings.length} cảnh báo</p></div></div><div className="editorial-metrics">{[['Giữ', report.counts.kept], ['Bỏ', report.counts.dropped], ['Nhịp', report.counts.beats], ['Ước tính', `~${report.counts.estimated_seconds} giây`]].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
          {report.errors.length ? <IssueList title="Lỗi cần sửa" items={report.errors} onJump={jump} tone="error" /> : null}{report.warnings.length ? <IssueList title="Cần rà bằng ngữ cảnh" items={report.warnings} onJump={jump} tone="warning" /> : null}
          {report.dropped.length ? <details className="editorial-dropped"><summary>{report.dropped.length} comment bị bỏ khỏi curated</summary>{report.dropped.map(item => <article key={item.image}><strong>@{item.handle || '?'} · {item.image}</strong><p>{item.text}</p></article>)}</details> : null}
          <Notice>{report.limit}</Notice><div className="editorial-report-actions"><Button icon="download" disabled={!report.valid} onClick={() => downloadText('tts-cleaned.txt', draft.cleaned)}>Tải bản đã kiểm tra</Button><Button icon="arrow" variant="primary" loading={pending} disabled={!report.valid || restoredReport} onClick={useInEditor}>Dùng trong trình dựng Threads</Button></div><p className="muted small">Chuyển sang trình dựng chỉ nạp kịch bản và ảnh. Không tự render, không ghi đè pool nguồn.</p>
        </>}
      </div></Card>}
    </div><aside className="editorial-aside"><Card className="panel editorial-helper"><div className="panel-heading"><h2>Làm với LLM bên ngoài</h2><Icon name="link" size={18} /></div><div><p>Chép prompt và dữ liệu, xử lý ở LLM bạn chọn rồi dán kết quả vào đúng ô. Hai bước không tự chạy trong app.</p><Button variant="outline" icon="link" disabled={!draft.session || rawChanged} onClick={() => setPrompt({ title: 'Prompt curate · giữ nguyên chữ', text: curatePrompt(draft.source_text) })}>Prompt cho bước ② Curate</Button><Button variant="outline" icon="audio" disabled={!draft.curated.trim() || rawChanged} onClick={() => setPrompt({ title: 'Prompt normalize · quy tắc TTS', text: normalizePrompt(draft.source_text, draft.curated) })}>Prompt cho bước ③ Normalize</Button><small>Bản nháp giữ khi đổi màn hình trong phiên. Tải .txt để lưu riêng trước khi tải lại app.</small></div></Card>
      {draft.session ? <Card className="panel editorial-tree"><div className="panel-heading"><h2>Cây nguồn</h2><Badge variant="secondary">{draft.counts.comments} comment</Badge></div><div className="tree-summary">{draft.counts.groups} cụm hội thoại · không tự loại comment</div><div className="tree-scroll">{draft.tree.map((node, index) => <article key={`${node.image}-${index}`} style={{ marginInlineStart: `${Math.min(node.depth, 5) * 12}px` }}><span className="tree-dot" /><div><strong>{index === 0 ? 'Bài gốc' : `@${node.handle || '?'}`}</strong><p>{node.text || '(không có chữ)'}</p><small title={node.image}>{node.image}</small></div></article>)}</div>{draft.warnings.map(value => <Notice key={value}>{value}</Notice>)}</Card> : null}
    </aside></div>
    {prompt ? <Modal title={prompt.title} wide onClose={() => setPrompt(null)}><div className="editorial-prompt"><Field label="Prompt kèm dữ liệu để tự gửi LLM"><textarea rows={20} readOnly value={prompt.text} spellCheck={false} /></Field></div><div className="modal-footer"><Button icon="download" onClick={() => downloadText('prompt.txt', prompt.text)}>Tải prompt</Button><Button icon="link" variant="primary" onClick={() => copy(prompt.text)}>Sao chép prompt</Button></div></Modal> : null}
  </>
}

function IssueList({ title, items, onJump, tone }) {
  return <section className={`editorial-issues ${tone}`}><h3>{title}</h3>{items.map((item, index) => <button key={`${item.code}-${item.line}-${index}`} onClick={() => onJump(item)}><span><Badge variant="outline">{item.stage === 'curated' ? '② Curate' : item.stage === 'cleaned' ? '③ Normalize' : '① Nguồn'}{item.line ? ` · dòng ${item.line}` : ''}</Badge><p>{item.message}</p></span><Icon name="arrow" size={16} /></button>)}</section>
}
