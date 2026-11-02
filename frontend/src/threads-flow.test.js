import test from 'node:test'
import assert from 'node:assert/strict'
import { receiveRawThread, receiveReviewedThread } from './threads-flow.js'

test('raw scan fills the Threads script box and keeps the raw source separate', () => {
  const input = Object.freeze({ script: '# post/main.png\nBản thô || -', session: 'raw-session', content: 'demo', images: [{ rel: 'post/main.png' }] })
  const state = receiveRawThread({}, input)
  assert.equal(state.script, input.script)
  assert.equal(state.approved, false)
  assert.deepEqual(state.rows, [])
  assert.equal(state.rawScript, input.script)
  assert.equal(state.rawSession, input.session)
  assert.deepEqual(state.images, input.images)
  assert.equal(input.script, '# post/main.png\nBản thô || -')
})

test('only reviewed handoff fills Threads and preserves the original editorial input', () => {
  const raw = receiveRawThread({}, { script: 'Thô', session: 'raw', content: 'demo' })
  const reviewed = receiveReviewedThread(raw, { script: 'Đã chuẩn hóa || -', session: 'selected', rows: [[1, 'Đã chuẩn hóa', '-', 'post', 'post/main.png']] })
  assert.equal(reviewed.script, 'Đã chuẩn hóa || -')
  assert.equal(reviewed.approved, true)
  assert.equal(reviewed.session, 'selected')
  assert.equal(reviewed.rows.length, 1)
  assert.equal(reviewed.rawScript, raw.rawScript)
  assert.equal(reviewed.rawSession, raw.rawSession)
})

test('fetching a different post replaces the script and invalidates the prior preview', () => {
  const reviewed = { script: 'Bản cũ', approved: true, rows: [[1]], frame: { url: '/old.png' }, output: { url: '/old.mp4' } }
  const next = receiveRawThread(reviewed, { script: 'Bản thô mới', session: 'new', content: 'new-post' })
  assert.equal(next.script, 'Bản thô mới')
  assert.equal(next.approved, false)
  assert.equal(next.frame, null)
  assert.equal(next.output, null)
  assert.deepEqual(next.rows, [])
  assert.equal(next.rawScript, 'Bản thô mới')
})
