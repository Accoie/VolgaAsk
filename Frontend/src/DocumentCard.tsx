import { useState } from 'react'
import type { Turn } from './api'
import { DocumentPreview } from './DocumentPreview'
import { MarkdownText } from './MarkdownText'

type Props = { chatId: string; turn: Turn; busy: boolean; revise: () => void }

export function DocumentCard({ chatId, turn, busy, revise }: Props) {
  const [preview, setPreview] = useState(false)
  const path = `chats/${chatId}/files/${turn.fileId}`

  return <section className="document-card"><h3>{turn.documentTitle}</h3>
    <small>DOCX · Готов к скачиванию</small>
    <button className="preview-button" onClick={() => setPreview(true)}>Предпросмотр</button>
    {preview && <DocumentPreview url={'/api/' + path} title={turn.documentTitle || 'Документ'}
      fallback={turn.preview} close={() => setPreview(false)} />}
    <h4>Результат проверки</h4><MarkdownText text={turn.report || 'Отчёт пока не получен.'} />
    <div className="actions"><a href={'/api/' + path} download>Скачать DOCX</a>
      <button disabled={busy} onClick={revise}>Доработать</button></div>
    {turn.report && <small>Замечания ИИ носят предварительный характер.</small>}
  </section>
}
