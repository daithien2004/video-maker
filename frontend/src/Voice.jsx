import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Empty, Icon } from './ui'
import { editSpokenDraft } from './script-preparation'

const spokenOf = (row, threads) => {
  const spoken = String(row?.[1] ?? '').replace(/\*/g, '').trim()
  return spoken || (threads && row?.[4] ? '[sound]' : '')
}

function clock(seconds) {
  const total = Math.round(seconds)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

export const voiceSignature = settings => JSON.stringify([settings.backend, settings.voice || '', Number(settings.speed).toFixed(2)])
export const voiceLines = (rows, threads) => rows
  .map((row, rowIndex) => ({ row, rowIndex, text: row?.length >= 5 ? spokenOf(row, threads) : '' })).filter(line => line.text)
  .map((line, index) => ({ ...line, beat: index + 1, sound: threads && ['[sound]', '[zoom]'].includes(line.text) }))
export const voiceReady = (line, item, signature) => Boolean(item && item.text === line.text &&
  (line.sound ? item.kind === 'sfx' : item.file && item.signature === signature))

export default function Voice({ draft, update, body, work, notify, settings, threads, sourceReady }) {
  const [playing, setPlaying] = useState(null)
  const [pending, setPending] = useState(null)
  const [editing, setEditing] = useState(null)
  const audio = useRef()
  const auto = useRef(false)

  const signature = voiceSignature(settings)
  const lines = useMemo(() => voiceLines(draft.voiceRows || [], threads), [draft.voiceRows, threads])
  const items = useMemo(() => new Map((draft.voice || []).map(item => [item.beat, item])), [draft.voice])
  const ready = lines.filter(line => voiceReady(line, items.get(line.beat), signature)).length
  const total = lines.reduce((sum, line) => sum + (items.get(line.beat)?.seconds || 0), 0)

  useEffect(() => { if (!work.busy) setPending(null) }, [work.busy])
  useEffect(() => () => { audio.current?.pause(); auto.current = false }, [])

  function stop() {
    auto.current = false
    audio.current?.pause()
    setPlaying(null)
  }

  function generate(beat = null, nextDraft = draft) {
    stop()
    if (!sourceReady) return
    setPending(beat ?? 'all')
    const payload = { ...body(), script: nextDraft.preparedScript, rows: nextDraft.voiceRows,
      index: beat === null ? null : beat - 1, force: beat !== null }
    work.run('/voice', payload, result => {
      update(current => {
        if (current.preparedScript !== payload.script) return current
        const merged = beat === null ? [] : [...(current.voice || [])]
        result.items.forEach(resultItem => {
          const item = { ...resultItem, signature }
          const at = merged.findIndex(old => old.beat === item.beat)
          if (at >= 0) merged[at] = item
          else merged.push(item)
        })
        return { ...current, voice: merged.sort((a, b) => a.beat - b.beat) }
      })
      notify(result.message)
    })
  }

  function editLine(line) {
    stop()
    setEditing({ rowIndex: line.rowIndex, text: line.text })
  }

  function saveLine(line, regenerate) {
    try {
      const next = editSpokenDraft(draft, line.rowIndex, editing.text, threads)
      stop()
      update(current => current.script === draft.script ? next : current)
      setEditing(null)
      if (regenerate) generate(line.beat, next)
      else notify('Đã đồng bộ lời đọc với kịch bản. Bấm Tạo lại để cập nhật voice đoạn này.')
    } catch (error) { notify(error.message, 'error') }
  }

  function play(beat, continuous = false) {
    auto.current = continuous
    const element = audio.current
    const item = items.get(beat)
    if (!element || !item?.file) return
    if (playing === beat) { element.pause(); auto.current = false; setPlaying(null); return }
    element.src = `${item.file.url}&v=${item.file.modified}`
    element.play().catch(() => { stop(); notify('Không phát được file giọng đọc.', 'error') })
    setPlaying(beat)
  }

  function playAll() {
    const first = lines.find(line => items.get(line.beat)?.file)
    if (!first) return notify('Chưa có nhịp nào được tạo giọng đọc.', 'error')
    if (playing !== null && auto.current) return stop()
    play(first.beat, true)
  }

  function ended() {
    if (!auto.current) return setPlaying(null)
    const next = lines.find(line => line.beat > playing && items.get(line.beat)?.file)
    if (!next) { auto.current = false; return setPlaying(null) }
    const element = audio.current
    element.src = `${items.get(next.beat).file.url}&v=${items.get(next.beat).file.modified}`
    element.play().catch(stop)
    setPlaying(next.beat)
  }

  if (!lines.length) return <Empty icon="audio" title="Chưa có voice">Bấm “Tạo nhịp và voice” ở tab Kịch bản để chuẩn bị cả hai.</Empty>

  return <>
    <div className="voice-toolbar">
      <div className="voice-summary"><strong>{ready}<small> / {lines.length}</small></strong><span>nhịp đã có giọng đọc{total ? ` · ${clock(total)}` : ''}</span></div>
      <div className="voice-toolbar-actions">
        <Button icon="play" variant="subtle" disabled={!lines.some(line => items.get(line.beat)?.file) || work.busy} onClick={playAll}>Nghe liên tục</Button>
        <Button icon="stop" variant="outline" disabled={playing === null} onClick={stop}>Dừng nghe</Button>
        <Button icon="audio" variant="primary" loading={pending === 'all'} disabled={work.busy || !sourceReady} onClick={() => generate()}>Cập nhật voice theo giọng đã chọn</Button>
      </div>
    </div>
    <div className="voice-list">
      {lines.map(line => {
        const item = items.get(line.beat)
        const sfx = line.sound
        const stale = Boolean(item) && !voiceReady(line, item, signature)
        const state = !item ? 'todo' : stale ? 'stale' : item.cached ? 'cached' : 'fresh'
        return <article key={line.beat} className={`voice-line ${playing === line.beat ? 'playing' : ''}`}>
          <button className="voice-play" aria-label={playing === line.beat ? `Dừng nhịp ${line.beat}` : `Nghe nhịp ${line.beat}`} disabled={!item?.file} onClick={() => play(line.beat)}>
            <Icon name={playing === line.beat ? 'stop' : 'play'} size={15} />
          </button>
          <div className="voice-text">
            <span className="voice-beat">NHỊP {String(line.beat).padStart(2, '0')}</span>
            {editing?.rowIndex === line.rowIndex ? <div className="voice-inline-edit">
              <textarea rows={3} aria-label={`Sửa lời đọc nhịp ${line.beat}`} value={editing.text} disabled={work.busy} onChange={event => setEditing({ ...editing, text: event.target.value })} autoFocus />
              <small>Lưu sẽ cập nhật đúng dòng trong kịch bản tổng và lời đọc của nhịp này; giữ nguyên hình và chữ hiển thị.</small>
              <div className="voice-toolbar-actions">
                <Button icon="refresh" variant="primary" disabled={work.busy || !sourceReady} onClick={() => saveLine(line, true)}>Lưu và tạo lại voice</Button>
                <Button icon="save" disabled={work.busy || !sourceReady} onClick={() => saveLine(line, false)}>Lưu lời đọc</Button>
                <Button disabled={work.busy} onClick={() => setEditing(null)}>Hủy</Button>
              </div>
            </div> : <p>{sfx ? 'Âm thanh chuyển cảnh, không có giọng đọc.' : line.text}</p>}
          </div>
          <div className="voice-meta">
            <span className={`voice-chip ${state}`}>{state === 'todo' ? 'chưa tạo' : state === 'stale' ? 'cần tạo lại' : state === 'cached' ? 'đã có' : 'mới tạo'}</span>
            {item?.seconds ? <small>{item.seconds.toFixed(1)}s</small> : null}
            {!sfx && editing?.rowIndex !== line.rowIndex ? <Button variant="subtle" disabled={work.busy || !sourceReady || !Number.isInteger(draft.sourceLines?.[line.rowIndex])} onClick={() => editLine(line)}>Sửa lời đọc</Button> : null}
            {sfx ? null : <Button icon="refresh" variant="subtle" loading={pending === line.beat} disabled={work.busy || !sourceReady} onClick={() => generate(line.beat)}>{item ? 'Tạo lại' : 'Tạo'}</Button>}
          </div>
        </article>
      })}
    </div>
    <audio ref={audio} onEnded={ended} onError={stop} controls aria-label="Voice" style={{ width: '100%', marginTop: 16 }} />
  </>
}
