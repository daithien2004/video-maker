const spokenText = value => value.replace(/\*/g, '').trim()

export function mapSourceLines(script, rows, threads = false) {
  let image = ''
  const candidates = []
  script.split(/\r?\n/).forEach((raw, lineIndex) => {
    let text = raw.trim()
    if (!text) return
    if (text.startsWith('#')) {
      if (threads) image = text.replace(/^#+\s*/, '').split(/\s/)[0]
      return
    }
    if (threads && !image) return
    if (!threads) text = text.replace(/^\[[^\]]*\]\s*/, '')
    const spoken = spokenText(text.split('||')[0])
    if (spoken || threads) candidates.push({ lineIndex, spoken: spoken || '[sound]', image })
  })
  let cursor = 0
  return rows.map(row => {
    const candidate = candidates[cursor]
    if (candidate && candidate.spoken === spokenText(String(row[1] || '')) &&
        (!threads || candidate.image === row[4])) {
      cursor += 1
      return candidate.lineIndex
    }
    return null // Auto-generated sound/zoom rows have no editable source line.
  })
}

export function prepareScriptDraft(current, data, script, content, threads = false) {
  if (current.script !== script || (current.content ?? content) !== content) return current
  return {
    ...current, rows: data.rows.map(row => [...row]),
    voiceRows: data.rows.map(row => [...row]), voice: [], beats: data.beats,
    preparedScript: script, preparedContent: data.content ?? content,
    sourceLines: mapSourceLines(script, data.rows, threads),
    session: data.session || current.session, content: data.content ?? content,
    note: data.message || '', frame: null, output: null, selected: 0,
  }
}

export function editSpokenDraft(draft, rowIndex, value, threads = false) {
  if (draft.script !== draft.preparedScript) throw new Error('Hãy tạo nhịp và voice từ kịch bản mới trước khi sửa từng đoạn.')
  const text = value.trim()
  if (!text || /[\r\n]/.test(text) || text.includes('||') || text.startsWith('#') ||
      ['[sound]', '[zoom]'].includes(spokenText(text)) || (!threads && text.startsWith('['))) {
    throw new Error('Nhập một đoạn lời đọc, không để trống hoặc dùng ký hiệu chia nhịp.')
  }
  const sourceLine = draft.sourceLines?.[rowIndex]
  if (!Number.isInteger(sourceLine)) throw new Error('Không tìm thấy dòng kịch bản tương ứng. Hãy tạo nhịp và voice lại.')
  const lines = draft.script.split(/\r?\n/)
  const original = lines[sourceLine]
  const prefix = threads ? original.match(/^\s*/)[0] : original.match(/^\s*(?:\[[^\]]*\]\s*)?/)[0]
  const delimiter = original.indexOf('||')
  const suffix = delimiter >= 0 ? original.slice(delimiter) : `|| ${original.slice(prefix.length).trim()}`
  lines[sourceLine] = `${prefix}${text} ${suffix}`
  const script = lines.join(draft.script.includes('\r\n') ? '\r\n' : '\n')
  const spoken = spokenText(text)
  const patchRows = rows => rows.map((row, index) => index === rowIndex ? row.map((cell, col) => col === 1 ? spoken : cell) : row)
  return { ...draft, script, preparedScript: script, rows: patchRows(draft.rows),
    voiceRows: patchRows(draft.voiceRows), frame: null, output: null }
}

export function sourceIsPrepared(draft, content) {
  return draft.preparedScript === draft.script && draft.preparedContent === content
}

export function renderRows(draft) {
  if (draft.rows.length !== draft.voiceRows?.length) throw new Error('Cần tạo nhịp và voice lại từ kịch bản.')
  return draft.rows.map((row, index) => {
    const result = [...row]
    result[1] = draft.voiceRows[index][1]
    return result
  })
}
