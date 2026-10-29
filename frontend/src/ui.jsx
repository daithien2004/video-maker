import React from 'react'
import { Button as ShadcnButton } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { NativeSelect } from '@/components/ui/native-select'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

export { Badge } from '@/components/ui/badge'
export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
export { Switch } from '@/components/ui/switch'

const paths = {
  film: 'M4 3h16v18H4z M4 8h16 M4 16h16 M8 3v5 M16 3v5 M8 16v5 M16 16v5',
  play: 'M9 5l11 7-11 7z',
  layers: 'M12 3L2 8l10 5 10-5-10-5z M2 12l10 5 10-5 M2 16l10 5 10-5',
  library: 'M3 4h5v16H3z M11 4h4v16h-4z M18 4l4 15-4 1-4-15',
  threads: 'M18.5 8c-1-4-9-5-12-1-4 6-1 14 6 14 7 0 9-7 4-10-5-3-10 2-6 4 3 2 7-2 5-7',
  export: 'M12 16V3 M7 8l5-5 5 5 M4 14v6h16v-6',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M10 2h4l1 3 3 1 3 3-2 3 1 3-3 3-3-1-3 2-3-3-1-3-3-1V9l3-1 1-3 2-1z',
  check: 'M5 12l4 4L19 6',
  arrow: 'M5 12h14 M14 7l5 5-5 5',
  plus: 'M12 5v14 M5 12h14',
  close: 'M6 6l12 12 M18 6L6 18',
  save: 'M4 3h13l4 4v14H3V3z M7 3v6h10V3 M7 21v-8h10v8',
  refresh: 'M20 7a9 9 0 1 0 1 9 M20 2v6h-6',
  image: 'M3 3h18v18H3z M3 16l6-6 8 11 M13 16l4-4 4 4 M15 7h.01',
  search: 'M11 3a8 8 0 1 0 0 16 8 8 0 0 0 0-16 M17 17l5 5',
  upload: 'M12 16V3 M7 8l5-5 5 5 M3 16v5h18v-5',
  download: 'M12 3v13 M7 11l5 5 5-5 M3 17v4h18v-4',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
  chevron: 'M9 5l7 7-7 7',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 10v7 M12 7h.01',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2',
  trash: 'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7',
  audio: 'M4 10v4 M8 6v12 M12 3v18 M16 6v12 M20 10v4',
  facebook: 'M14 21v-8h3l1-4h-4V7c0-2 1-2 4-2V2h-3c-4 0-5 2-5 5v2H7v4h3v8',
  monitor: 'M2 3h20v14H2z M8 22h8 M12 17v5',
  folder: 'M2 5h8l2 3h10v12H2z',
  up: 'M6 15l6-6 6 6',
  down: 'M6 9l6 6 6-6',
  link: 'M10 14l4-4 M8 16l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0 M16 8l1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5L19 19 M5 19l1.5-1.5 M17.5 6.5L19 5',
  moon: 'M20.5 13a8.5 8.5 0 1 1-9.5-9.5A7 7 0 0 0 20.5 13z',
}

export function Icon({ name, size = 19, ...props }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name] || paths.film} /></svg>
}

export function Button({ children, icon, variant = '', className = '', loading, ...props }) {
  const mapped = variant.includes('danger') ? 'destructive' : ({ primary: 'default', subtle: 'ghost', outline: 'outline', secondary: 'secondary', '': 'secondary' }[variant] || variant)
  return <ShadcnButton variant={mapped} className={cn('button', variant, className)} {...props} disabled={props.disabled || loading} aria-busy={loading || undefined}>
    {loading ? <span className="spinner" /> : icon ? <Icon name={icon} size={17} /> : null}{children}
  </ShadcnButton>
}

export function Field({ label, hint, children, className = '' }) {
  const id = React.useId()
  return <div className={cn('field', className)}><Label htmlFor={`${id}-control`} id={id}>{label}</Label>{React.Children.map(children, child => {
    if (!React.isValidElement(child) || !['input', 'select', 'textarea'].includes(child.type)) return child
    const props = { ...child.props, id: `${id}-control`, 'aria-labelledby': id, 'aria-describedby': hint ? `${id}-hint` : undefined }
    if (child.type === 'textarea') return <Textarea {...props} />
    if (child.type === 'select') return <NativeSelect {...props} />
    if (!['range', 'checkbox', 'file', 'color'].includes(child.props.type)) return <Input {...props} />
    return React.cloneElement(child, props)
  })}{hint ? <small id={`${id}-hint`}>{hint}</small> : null}</div>
}

export function Empty({ icon = 'folder', title, children, action }) {
  return <div className="empty"><div className="empty-symbol"><Icon name={icon} size={27} /></div><h3>{title}</h3><p>{children}</p>{action}</div>
}

export function Modal({ title, children, onClose, wide = false }) {
  const previous = React.useRef(document.activeElement)
  return <Dialog open onOpenChange={open => { if (!open) onClose() }}><DialogContent className={cn('modal', wide && 'wide')} showCloseButton={false} aria-describedby={undefined} onCloseAutoFocus={event => { event.preventDefault(); previous.current?.focus() }}>
    <div className="modal-head"><DialogTitle>{title}</DialogTitle><ShadcnButton type="button" variant="ghost" size="icon" className="icon-button" aria-label="Đóng" onClick={onClose}><Icon name="close" /></ShadcnButton></div>
    {children}
  </DialogContent></Dialog>
}

export function Media({ file, controls = false, className = '', ...props }) {
  if (!file) return null
  if (file.type?.startsWith('video/')) return <video className={className} src={file.url} controls={controls} preload="metadata" playsInline {...props} />
  if (file.type?.startsWith('audio/')) return <audio src={file.url} controls={controls} preload="metadata" {...props} />
  if (file.type?.startsWith('image/')) return <img className={className} src={file.url} alt={file.name} loading="lazy" {...props} />
  return <div className="file-symbol"><Icon name="folder" size={32} /></div>
}

export function Notice({ children, tone = '' }) {
  return children ? <div className={`notice ${tone}`}><Icon name="info" size={17} /><span>{typeof children === 'string' ? children.replace(/\*\*|`/g, '') : children}</span></div> : null
}
