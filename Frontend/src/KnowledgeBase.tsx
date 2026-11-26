import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, post } from './api'

type Entry = { id: string; title: string; filename: string; date?: string; status: string; errorCode?: string; ocrApplied: boolean }
type Candidate = { title: string; filename: string; url: string; checksum?: string; inLibrary: boolean; otherCopy: boolean }
type Catalog = { documents: Candidate[]; sync?: { refreshed?: string; error?: string } }
const states: Record<string, string> = {
  queued: 'В очереди', indexing: 'Обрабатывается', ready: 'В базе', deleting: 'Удаляется', failed: 'Не добавлен'
}
const errors: Record<string, string> = {
  checker_unavailable: 'Локальная модель проверки текста недоступна. Повторите загрузку позже.',
  too_many_pages: 'Документ содержит более 2000 страниц. Разделите его на части.',
  unreadable_text: 'Не удалось распознать связный текст. Попробуйте загрузить более чёткий скан или PDF с текстовым слоем.',
  ocr_failed: 'Не удалось обработать скан. Проверьте, что PDF открывается, и попробуйте загрузить его снова.',
  ocr_timeout: 'Распознавание заняло слишком много времени. Разделите PDF на части и загрузите их отдельно.',
  ocr_unavailable: 'Распознавание временно недоступно. Повторите загрузку позже.',
  invalid_pdf: 'Файл не является PDF.', conversion_failed: 'Не удалось прочитать PDF. Проверьте файл и защиту паролем.',
  portal_changed: 'На портале появилась другая версия. Дождитесь обновления каталога.',
  download_failed: 'Не удалось скачать документ с портала.', index_failed: 'Ошибка индексации. Попробуйте загрузить документ ещё раз.'
}

function EyeIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
}

export function KnowledgeBase() {
  const [tab, setTab] = useState<'library' | 'portal'>('library')
  const [entries, setEntries] = useState<Entry[]>([])
  const [catalog, setCatalog] = useState<Catalog>({ documents: [] })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [removing, setRemoving] = useState('')
  const [search, setSearch] = useState('')
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const [docs, portal] = await Promise.all([
      api<Entry[]>('kb/documents', { signal }), api<Catalog>('kb/catalog', { signal })
    ])
    setEntries(docs)
    setCatalog(portal)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const signal = controller.signal
    async function watch() {
      while (!signal.aborted) {
        try {
          await refresh(signal)
          await api('kb/changes', { signal })
        } catch (err) {
          if (signal.aborted) return
          setError((err as Error).message)
          await new Promise(resolve => setTimeout(resolve, 5000))
        }
      }
    }
    void watch()
    return () => controller.abort()
  }, [refresh])

  async function change(action: () => Promise<unknown>) {
    setBusy(true)
    setError('')
    try { await action(); await refresh() }
    catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }

  function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    void change(async () => {
      await api('kb/upload', { method: 'POST', body: data })
      form.reset()
    })
  }

  const query = search.trim().toLocaleLowerCase()
  const filteredEntries = entries.filter(doc =>
    `${doc.title} ${doc.filename}`.toLocaleLowerCase().includes(query))
  const filteredCandidates = catalog.documents.filter(doc =>
    `${doc.title} ${doc.filename}`.toLocaleLowerCase().includes(query))

  return <section className="kb">
    <div className="actions"><button aria-pressed={tab === 'library'} onClick={() => setTab('library')}>В базе</button>
      <button aria-pressed={tab === 'portal'} onClick={() => setTab('portal')}>Доступные с портала</button></div>
    <input className="kb-search" type="search" aria-label="Поиск по документам"
      placeholder="Поиск по названию или имени файла" value={search}
      onChange={event => setSearch(event.target.value)} />
    {error && <p role="alert">{error}</p>}
    {tab === 'library' ? <>
      <details><summary>Загрузить свой PDF</summary><form onSubmit={upload}>
        <label>Официальное название<input name="title" maxLength={500} required /></label>
        <label>Дата документа<input name="date" type="date" required /></label>
        <label>Файл PDF до 48 МБ<input name="file" type="file" accept=".pdf,application/pdf" required /></label>
        <button className="primary" disabled={busy}>Добавить в очередь</button></form></details>
      {!entries.length ? <p>Документов пока нет.</p> : !filteredEntries.length ? <p>Документы не найдены.</p> : null}
      {filteredEntries.map(doc => <div className="row" key={doc.id}><div><strong>{doc.title}</strong>
        <small>{doc.filename} · {doc.date || 'Дата не указана'} · {states[doc.status]}
          {doc.ocrApplied && ' · Текст распознан'}</small>
        {doc.errorCode && <p role="alert">{errors[doc.errorCode] || 'Не удалось обработать документ.'}</p>}</div>
        <div className="actions">{doc.status === 'ready' && <a className="kb-preview-link"
          href={'/api/kb/documents/' + doc.id + '/file'} target="_blank" rel="noreferrer"
          aria-label={`Просмотреть документ: ${doc.title}`} title="Просмотреть документ"><EyeIcon /></a>}
          {['ready', 'failed'].includes(doc.status) && (removing === doc.id ? <>
            <button disabled={busy} onClick={() => void change(async () => {
              await api('kb/documents/' + doc.id, { method: 'DELETE' }); setRemoving('')
            })}>Подтвердить удаление</button><button onClick={() => setRemoving('')}>Отмена</button></> :
            <button onClick={() => setRemoving(doc.id)}>Удалить</button>)}</div></div>)}
    </> : <>
      {catalog.sync?.error && <p role="status">{catalog.sync.error}</p>}
      {!catalog.documents.length ? <p>Каталог портала пока не загружен.</p> : !filteredCandidates.length ? <p>Документы не найдены.</p> : null}
      {filteredCandidates.map(doc => <div className="row" key={doc.url}><div><div className="kb-document-title"><strong>{doc.title}</strong>
        <a className="kb-preview-link" href={doc.url} target="_blank" rel="noreferrer"
          aria-label={`Просмотреть документ: ${doc.title}`} title="Просмотреть документ">
          <EyeIcon />
        </a>
      </div>
        <small>{doc.filename}</small>{doc.otherCopy && !doc.inLibrary && <small>В базе есть другая копия с таким именем или источником.</small>}</div>
        {doc.inLibrary ? <small>Уже добавлен</small> : <button disabled={busy || !doc.checksum}
          onClick={() => void change(async () => {
            await api('kb/import', post({ url: doc.url, checksum: doc.checksum }))
            setTab('library')
          })}>{doc.checksum ? 'Добавить' : 'PDF не проверен'}</button>}</div>)}
    </>}
  </section>
}
