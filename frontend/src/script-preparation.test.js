import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareScriptDraft, sourceIsPrepared, renderRows, editSpokenDraft, mapSourceLines } from './script-preparation.js'

const initial = () => ({ script: 'original', content: 'demo', rows: [], session: '' })
const data = () => ({ rows: [[1, 'speech', 'caption', '', 'image.png']], beats: [] })

test('visual edits cannot mutate the script voice source', () => {
  const draft = prepareScriptDraft(initial(), data(), 'original', 'demo')
  draft.rows[0][1] = 'accidental visual speech change'
  draft.rows[0][2] = 'new caption'
  draft.rows[0][4] = 'other.png'
  assert.equal(draft.voiceRows[0][1], 'speech')
  assert.deepEqual(renderRows(draft)[0].slice(1, 5), ['speech', 'new caption', '', 'other.png'])
  assert.equal(sourceIsPrepared(draft, 'demo'), true)
})

test('editing source blocks export until both outputs are prepared again', () => {
  const draft = prepareScriptDraft(initial(), data(), 'original', 'demo')
  draft.script = 'changed'
  assert.equal(sourceIsPrepared(draft, 'demo'), false)
  const next = prepareScriptDraft(draft, data(), 'changed', 'demo')
  assert.equal(sourceIsPrepared(next, 'demo'), true)
  assert.deepEqual(next.voice, [])
})

test('a late response cannot replace a newer script', () => {
  const draft = { ...initial(), script: 'newer' }
  assert.equal(prepareScriptDraft(draft, data(), 'original', 'demo'), draft)
})

test('replacing audio leaves visual edits intact', () => {
  const draft = prepareScriptDraft(initial(), data(), 'original', 'demo')
  draft.rows[0][2] = 'custom caption'
  const updated = { ...draft, voice: [{ beat: 1, file: { url: '/new.wav' } }] }
  assert.equal(updated.rows[0][2], 'custom caption')
  assert.equal(updated.voiceRows[0][1], 'speech')
})

test('inline correction updates only the matching duplicate line and keeps media, captions and other audio', () => {
  const script = '# comment\r\n[tag] repeated || *Caption*\r\n\r\n[tag] repeated || -\r\n'
  const rows = [[1, 'repeated', 'Caption', 'tag', 'a.png'], [2, 'repeated', '-', 'tag', 'b.png']]
  const draft = prepareScriptDraft({ ...initial(), script }, { rows, beats: [] }, script, 'demo')
  draft.rows[1][4] = 'custom.png'
  draft.voice = [{ beat: 1, text: 'repeated' }, { beat: 2, text: 'repeated' }]
  const next = editSpokenDraft(draft, 1, 'corrected')
  assert.equal(next.script, '# comment\r\n[tag] repeated || *Caption*\r\n\r\n[tag] corrected || -\r\n')
  assert.equal(next.preparedScript, next.script)
  assert.equal(next.voiceRows[1][1], 'corrected')
  assert.equal(next.rows[1][1], 'corrected')
  assert.equal(next.rows[1][4], 'custom.png')
  assert.equal(next.rows[1][2], '-')
  assert.equal(next.voice, draft.voice)
  assert.equal(next.voice[1].text, 'repeated') // Stale audio is detected until regenerated.
  assert.equal(sourceIsPrepared(next, 'demo'), true)
})

test('Threads mapping skips inserted zoom and finds the correct section with repeated text', () => {
  const script = '# a.png (post)\nsame || -\n# b.png\nsame || -'
  const rows = [[1, 'same', '-', '', 'a.png'], [2, '[zoom]', '-', '', 'a.png'], [3, 'same', '-', '', 'b.png']]
  assert.deepEqual(mapSourceLines(script, rows, true), [1, null, 3])
  const draft = prepareScriptDraft({ ...initial(), script }, { rows, beats: [] }, script, 'demo', true)
  const next = editSpokenDraft(draft, 2, 'fixed', true)
  assert.equal(next.script, '# a.png (post)\nsame || -\n# b.png\nfixed || -')
  assert.equal(next.voiceRows[1][1], '[zoom]')
})

test('implicit captions stay intact when speech is corrected', () => {
  const script = '[tag] Original words'
  const draft = prepareScriptDraft({ ...initial(), script }, { rows: [[1, 'Original words', 'Original words', 'tag', '']], beats: [] }, script, 'demo')
  const next = editSpokenDraft(draft, 0, 'Fixed words')
  assert.equal(next.script, '[tag] Fixed words || Original words')
  assert.equal(next.rows[0][2], 'Original words')
})

test('inline edits reject structural changes and a changed bulk source', () => {
  const script = 'words || -'
  const draft = prepareScriptDraft({ ...initial(), script }, { rows: [[1, 'words', '-', '', '']], beats: [] }, script, 'demo')
  for (const text of ['', 'new\nline', 'words || -', '[sound]', '# heading']) {
    assert.throws(() => editSpokenDraft(draft, 0, text))
  }
  assert.throws(() => editSpokenDraft({ ...draft, script: 'changed' }, 0, 'fixed'))
})
