import { useEffect, useRef, useState } from 'react'

type Props = { url: string; title: string; fallback?: string; close: () => void }

export function DocumentPreview({ url, title, fallback, close }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const frame = useRef<HTMLIFrameElement>(null)
  const [ready, setReady] = useState(false)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  useEffect(() => { dialog.current?.showModal() }, [])
  useEffect(() => {
    const page = frame.current?.contentDocument
    if (!ready || !page) return
    const controller = new AbortController()
    async function render(target: Document) {
      const response = await fetch(url, { signal: controller.signal })
      if (!response.ok) throw new Error('DOCX недоступен')
      const blob = await response.blob()
      const { renderAsync } = await import('docx-preview')
      if (controller.signal.aborted) return
      await renderAsync(blob, target.body, target.head, { useBase64URL: true, renderAltChunks: false })
      setLoading(false)
    }
    render(page).catch(() => {
      if (!controller.signal.aborted) { setFailed(true); setLoading(false) }
    })
    return () => controller.abort()
  }, [ready, url])
  return <dialog className="preview-dialog" ref={dialog} aria-label={title} onCancel={close}>
    <div className="preview-heading"><strong>{title}</strong><button onClick={close}>Закрыть</button></div>
    {loading && <div className="loading" role="status"><span className="spinner" aria-hidden="true" />Открываю DOCX…</div>}
    {failed ? <><p>Показываю текстовую версию документа.</p><div className="paper">{fallback}</div></> :
      <iframe title={title} ref={frame} sandbox="allow-same-origin" onLoad={() => setReady(true)}
        srcDoc={`<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: blob:; font-src data: blob:; style-src 'unsafe-inline'"><body style="margin:0"></body>`} />}
  </dialog>
}
