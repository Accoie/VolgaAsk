import { useEffect, useState } from 'react'
import { api, post } from './api'
import { KnowledgeBase } from './KnowledgeBase'
import { TemplateEditor, type EditorData } from './TemplateEditor'
import './templates.css'

type Template = { id: string; title: string; filename: string; revision: number }
type Source = { id: string; title: string; filename: string; url: string; template?: string }

export function DocumentManagement({ back }: { back: () => void }) {
  const [section, setSection] = useState<'kb' | 'templates'>('kb')
  const [editor, setEditor] = useState<EditorData>()
  if (editor) return <TemplateEditor key={editor.id} initial={editor} close={() => setEditor(undefined)} />
  return <main className="management"><button onClick={back}>← К чату</button>
    <h1>Управление документами</h1>
    <div className="management-tabs">
      <button aria-pressed={section === 'kb'} onClick={() => setSection('kb')}>База знаний</button>
      <button aria-pressed={section === 'templates'} onClick={() => setSection('templates')}>Шаблоны документов</button>
    </div>
    {section === 'kb' ? <KnowledgeBase /> : <TemplateLibrary edit={setEditor} />}
  </main>
}

function TemplateLibrary({ edit }: { edit: (data: EditorData) => void }) {
  const [portal, setPortal] = useState(false)
  const [library, setLibrary] = useState<Template[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [search, setSearch] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    setLoading(true); setError('')
    const task = portal ? api<Source[]>('templates/catalog', options).then(setSources)
      : api<Template[]>('templates', options).then(setLibrary)
    task.catch(e => { if (!options.signal.aborted) setError(e.message) })
      .finally(() => { if (!options.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [portal, refresh])

  async function open(id: string, source?: Source) {
    setOpening(true); setError('')
    try {
      if (source && !source.template) {
        id = (await api<{ id: string }>(`templates/catalog/${source.id}/import`, post())).id
      }
      edit(await api<EditorData>(`templates/${id}/editor`))
    } catch (e) { setError((e as Error).message) }
    finally { setOpening(false) }
  }

  const items = (portal ? sources : library).filter(item =>
    (item.title + ' ' + item.filename).toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
  return <section className="kb"><div className="actions">
    <button disabled={opening} aria-pressed={!portal} onClick={() => setPortal(false)}>В библиотеке</button>
    <button disabled={opening} aria-pressed={portal} onClick={() => setPortal(true)}>Бланки МФЦ</button>
  </div>
    <input className="kb-search" type="search" aria-label="Поиск шаблонов" placeholder="Поиск по названию или имени файла"
      value={search} onChange={e => setSearch(e.target.value)} />
    {error && <p role="alert">{error} <button onClick={() => setRefresh(n => n + 1)}>Повторить</button></p>}
    {loading ? <p role="status">Загружаю список…</p> : <>
      {!items.length && !error && <p>Бланки не найдены.</p>}
      {items.map(item => <div className="row" key={item.id}><div><strong>{item.title}</strong>
        <small>{item.filename}{'revision' in item && (item.revision ? ' · Доступен в чате' : ' · Черновик')}</small></div>
        <div className="actions">{'url' in item ? <>
          <a href={item.url} target="_blank" rel="noreferrer">Скачать бланк</a>
          <button disabled={opening} onClick={() => open(item.template || '', item)}>
            {item.template ? 'Открыть шаблон' : 'Составить шаблон'}</button></> :
          <button disabled={opening} onClick={() => open(item.id)}>Открыть редактор</button>}</div>
      </div>)}</>}
  </section>
}
