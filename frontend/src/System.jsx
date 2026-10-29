import React, { useState } from 'react'
import { Button, Card, Icon, Notice } from './ui'

export default function System({ boot, work }) {
  const [report, setReport] = useState('')
  return <><section className="page-heading"><div><div className="eyebrow"><span /> STUDIO HEALTH</div><h1>Sẵn sàng cho video tiếp theo.</h1><p>Kiểm tra bộ dựng hình, giọng đọc và trạng thái kết nối.</p></div><Button variant="primary" icon="refresh" disabled={work.busy} onClick={() => work.run('/system/check', {}, result => setReport(result.message))}>Kiểm tra máy</Button></section>
    <div className="system-grid">{[['film', 'Bộ dựng video', 'FFmpeg · H.264 · 1080 × 1920', 'Dựng hình, ghép âm thanh, phụ đề và xuất video.'], ['audio', 'Giọng đọc', 'VieNeu-TTS', 'Giọng đọc tiếng Việt, điều chỉnh tốc độ theo kịch bản.'], ['threads', 'Phiên Threads', 'Trạng thái đăng nhập', boot.threads_status], ['facebook', 'Facebook Reels', boot.facebook.configured ? 'Đã có cấu hình kết nối' : 'Chưa cấu hình', 'Kiểm tra kết nối tại trang Facebook Reels.']].map(([icon, title, detail, text]) => <Card className="panel system-card" key={title}><div className="system-icon"><Icon name={icon} size={24} /></div><h3>{title}</h3><strong>{detail}</strong><p>{text}</p></Card>)}</div>
    {report ? <section className="panel system-report"><h2>Kết quả kiểm tra</h2><pre>{report}</pre></section> : <Notice>Bấm “Kiểm tra máy” để kiểm tra FFmpeg, bộ vẽ chữ, mã hóa GPU và thư viện giọng đọc.</Notice>}
  </>
}
