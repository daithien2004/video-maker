export async function request(path, body, options = {}) {
  const isForm = body instanceof FormData
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    ...options,
    headers: isForm || body === undefined ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
    ...(body === undefined ? {} : { body: isForm ? body : JSON.stringify(body) }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join('; ') : data.detail
    if (response.status === 404 && detail === 'Not Found' && path.startsWith('/editorial/')) {
      throw new Error('Máy chủ Python đang chạy bản cũ, chưa có chức năng Biên tập Threads. Đóng cửa sổ app rồi mở lại run.bat. Chỉ F5 trang sẽ không cập nhật máy chủ.')
    }
    throw new Error(detail || `Không thể thực hiện yêu cầu (${response.status}).`)
  }
  return data
}

export const size = bytes => bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(1)} GB` : `${(bytes / 1024 ** 2).toFixed(1)} MB`
export const date = value => new Date(value * 1000).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
export const download = file => `${file.url}&download=true`
