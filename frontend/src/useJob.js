import { useEffect, useRef, useState } from 'react'
import { request } from './api'

const STORAGE = 'videomaker.job.v1'
function stored() {
  try { return JSON.parse(localStorage.getItem(STORAGE)) } catch { return null }
}

export function useJob(notify, completed) {
  const [job, setJob] = useState(stored)
  const callback = useRef(null)
  const handlers = useRef({ notify, completed })
  handlers.current = { notify, completed }
  const busy = job?.status === 'queued' || job?.status === 'running' || job?.status === 'starting'
  const active = useRef(busy)
  active.current = busy

  useEffect(() => {
    if (!job?.id || !['queued', 'running', 'starting'].includes(job.status)) return
    let stopped = false
    let timer
    const controller = new AbortController()
    const poll = async () => {
      try {
        const next = await request(`/jobs/${job.id}`, undefined, { signal: controller.signal })
        if (stopped) return
        setJob(next)
        if (next.status === 'done' || next.status === 'error') {
          localStorage.removeItem(STORAGE)
          if (next.status === 'error') handlers.current.notify(next.message, 'error')
          else {
            const handler = callback.current
            callback.current = null
            if (handler) handler(next.result)
            else handlers.current.completed(next)
          }
          return
        }
        localStorage.setItem(STORAGE, JSON.stringify({ id: next.id, status: 'running', kind: next.kind }))
        timer = setTimeout(poll, 900)
      } catch (error) {
        if (stopped || error.name === 'AbortError') return
        if (error.message.includes('Tác vụ không còn')) {
          setJob({ id: job.id, status: 'error', message: error.message })
          localStorage.removeItem(STORAGE)
          handlers.current.notify('Máy chủ đã khởi động lại. Kiểm tra video đã xuất trước khi chạy lại tác vụ.', 'error')
          return
        }
        setJob(current => ({ ...current, message: 'Mất kết nối. Đang kết nối lại để theo dõi tác vụ…' }))
        timer = setTimeout(poll, 2500)
      }
    }
    poll()
    return () => { stopped = true; controller.abort(); clearTimeout(timer) }
  }, [job?.id])

  async function run(path, body, onDone) {
    if (active.current) return
    active.current = true
    setJob({ status: 'starting', progress: 0, message: 'Đang gửi yêu cầu…' })
    callback.current = onDone || null
    try {
      const { id } = await request(path, body)
      const next = { id, status: 'queued', progress: 0, message: 'Đang chờ xử lý…' }
      localStorage.setItem(STORAGE, JSON.stringify(next))
      setJob(next)
    } catch (error) {
      active.current = false
      setJob({ status: 'error', message: error.message })
      handlers.current.notify(error.message, 'error')
    }
  }
  return { job, busy, run }
}
