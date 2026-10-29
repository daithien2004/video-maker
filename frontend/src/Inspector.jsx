import React, { useState } from 'react'
import { Button, Field, Media, Modal, Switch } from './ui'

function Slider({ label, value, min, max, step = 1, onChange, unit = '' }) {
  return <Field label={<>{label}<b>{value}{unit}</b></>}><input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))} /></Field>
}

export default function Inspector({ settings: s, setSettings, voiceCatalog, setVoiceCatalog, boot, work, onClose, onApply, notify, threads }) {
  const voices = voiceCatalog[s.backend] || []
  const setVoices = voices => setVoiceCatalog(old => ({ ...old, [s.backend]: voices }))
  const [audio, setAudio] = useState(null)
  const [sample, setSample] = useState('Xin chào, đây là giọng đọc thử cho video của bạn.')
  const set = (key, value) => setSettings(old => ({ ...old, [key]: value }))
  const slider = (key, label, min, max, step, unit) => <Slider label={label} value={s[key]} min={min} max={max} step={step} unit={unit} onChange={v => set(key, v)} />
  const check = (key, label) => <label className="switch-row" htmlFor={`video-${key}`}><span>{label}</span><Switch id={`video-${key}`} checked={s[key]} onCheckedChange={value => set(key, value)} /></label>
  return <Modal title="Thiết lập video" onClose={onClose}>
    <div className="inspector-body">
      <section><h3><span>01</span> Giọng đọc</h3>
        <Field label="Bộ tạo giọng"><select value={s.backend} onChange={e => { set('backend', e.target.value); setAudio(null) }}><option value="vieneu">Giọng thật · VieNeu-TTS</option><option value="dummy">Chế độ thử · tiếng bíp</option></select></Field>
        <div className="field-inline"><Field label="Giọng đọc"><select value={s.voice} onChange={e => { set('voice', e.target.value); setAudio(null) }}><option value="">Mặc định</option>{s.voice && !voices.some(([, value]) => value === s.voice) ? <option value={s.voice}>{s.voice}</option> : null}{voices.filter(([, value]) => value !== '').map(([label, value]) => <option key={value} value={value}>{label}</option>)}</select></Field><Button icon="refresh" disabled={work.busy} onClick={() => work.run('/voices', { settings: s }, result => { setVoices(result.voices || []); notify(`Đã lấy ${result.voices?.length || 0} giọng. Mở ô “Giọng đọc” để chọn rồi nghe thử.`) })}>Lấy danh sách giọng</Button></div>
        <p className="muted small">{voices.length ? `Có ${voices.length} giọng. Bấm ô phía trên để chọn, rồi bấm “Nghe thử giọng”.` : 'Bấm “Lấy danh sách giọng” để xem các giọng có sẵn.'}</p>
        {slider('speed', 'Tốc độ đọc', .8, 1.4, .05, '×')}{slider('gap', 'Nghỉ giữa nhịp', 0, 2, .05, ' s')}
        <Field label="Nội dung nghe thử"><textarea rows={2} value={sample} onChange={e => setSample(e.target.value)} /></Field>
        <Button icon="audio" disabled={work.busy} onClick={() => work.run('/sample', { settings: s, script: sample }, result => setAudio(result.file))}>Nghe thử giọng</Button>{audio ? <Media file={audio} controls /> : null}
      </section>
      <section><h3><span>02</span> Nền & âm nhạc</h3><Field label="Video nền"><select value={s.bg} onChange={e => set('bg', e.target.value)}>{boot.backgrounds.map(bg => <option key={bg}>{bg}</option>)}</select></Field>
        {check('use_music', 'Dùng nhạc nền')}{s.use_music ? slider('music_vol', 'Âm lượng nhạc', .02, .4, .01) : null}
        {check('bg_motion', 'Nền phóng chậm (khung không đứng yên)')}{check('sfx', 'Tiếng pop khi card xuất hiện (video thường: whoosh)')}
        <Field label="Khung hình/giây"><select value={s.fps || 60} onChange={e => set('fps', Number(e.target.value))}><option value={30}>30 FPS · file nhẹ</option><option value={60}>60 FPS · chuyển động mượt</option></select></Field>
      </section>
      <section><h3><span>03</span> Chữ hiển thị</h3>
        <Field label="Tên font"><input value={s.font} onChange={e => set('font', e.target.value)} /></Field>
        <div className="three-fields">{[['text_color', 'Màu chữ'], ['outline_color', 'Viền chữ'], ['emph_color', 'Nhấn mạnh']].map(([key, label]) => <Field key={key} label={label}><input type="color" value={s[key]} onChange={e => set(key, e.target.value)} /></Field>)}</div>
        {slider('font_size', 'Cỡ chữ', 60, 200)}{slider('outline_w', 'Độ dày viền', 0, 20)}{slider('text_y', 'Vị trí chữ', 300, 1700)}{slider('max_words', 'Số từ mỗi cụm', 1, 8)}{slider('emph_scale', 'Cỡ nhấn mạnh', 1, 2, .05, '×')}
        {check('upper', 'Chuyển chữ IN HOA')}{check('pop', 'Hiệu ứng chữ bật lên')}{check('karaoke', 'Tô sáng từng từ khi đọc')}
      </section>
      <section><h3><span>04</span> Khung minh họa</h3><p className="muted small">Flow Threads tự dùng bố cục card riêng khi dựng video.</p>
        {slider('meme_y', 'Vị trí dọc', 0, 800)}{slider('meme_w', 'Chiều rộng', 300, 1080)}{slider('meme_h', 'Chiều cao', 200, 900)}
        {threads ? slider('threads_radius', 'Bo góc card Threads', 0, 80) : null}
        {threads ? slider('threads_side_margin', 'Lề ngang card Threads', 0, 120) : null}
        {threads ? slider('threads_shadow', 'Bóng đổ card Threads', 0, 100) : null}
        {check('card_motion', 'Card ảnh nở/trôi nhẹ')}{check('mascot', 'Mascot trồi lên ở đoạn mở đầu')}{check('pop_in', 'Card nảy vào khi sang mục (Threads)')}{check('carry', 'Giữ media ở nhịp không có thẻ')}{check('nvenc', 'Mã hóa bằng GPU NVIDIA')}
      </section>
    </div><div className="modal-footer"><Button onClick={onApply || onClose} variant="primary" icon="check">Áp dụng</Button></div>
  </Modal>
}
