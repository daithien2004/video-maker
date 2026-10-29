import test from 'node:test'
import assert from 'node:assert/strict'
import { request } from './api.js'

test('old backend missing editorial routes explains restart instead of bare Not Found', async () => {
  const original = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 })
  try { await assert.rejects(request('/editorial/history'), /run\.bat/) }
  finally { globalThis.fetch = original }
})

test('a real missing saved session retains its specific error', async () => {
  const original = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Phiên bài đã hết.' }), { status: 404 })
  try { await assert.rejects(request('/editorial/restore', { id: 'old' }), /Phiên bài đã hết/) }
  finally { globalThis.fetch = original }
})

test('successful editorial history remains unchanged', async () => {
  const original = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ items: [{ id: 'saved', stage: 2 }] }), { status: 200 })
  try { assert.deepEqual(await request('/editorial/history'), { items: [{ id: 'saved', stage: 2 }] }) }
  finally { globalThis.fetch = original }
})
