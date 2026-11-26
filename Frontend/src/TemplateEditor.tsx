import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, post, request } from './api'
import { DocumentPreview } from './DocumentPreview'

type Component = { key: string; label: string; required: boolean; question?: string }
type Block = { text: string; align?: string }
type Selection = { paragraph: number; start: number; end: number }
type Edit = Selection & { text: string; component?: string }
export type EditorData = { id: string; title: string; filename: string; revision: number; blocks: Block[]; components: Component[] }

const length = (text: string) => Array.from(text).length
const marker = (key: string) => '{{ ' + key + ' }}'

function paragraphs(initial: Block[], edits: Edit[]) {
  const blocks = initial.map(block => ({ ...block }))
  for (const edit of edits) {
    const block = blocks[edit.paragraph]
    const chars = Array.from(block.text)
    const value = edit.component ? marker(edit.component) : edit.text
    block.text = chars.slice(0, edit.start).join('') + value + chars.slice(edit.end).join('')
  }
  return blocks
}

function boundary(row: HTMLElement, node: Node, offset: number, end: boolean) {
  if (node === row) return Number((row.children[offset] as HTMLElement)?.dataset.start ?? row.dataset.length)
  const span = (node instanceof HTMLElement ? node : node.parentElement)?.closest<HTMLElement>('[data-start]')
  if (!span) return 0
  const start = Number(span.dataset.start)
  if (span.dataset.key) return end ? Number(span.dataset.end) : start
  const range = document.createRange()
  range.selectNodeContents(span)
  range.setEnd(node, offset)
  return start + length(range.toString())
}

function readSelection(paper: HTMLElement): Selection | undefined {
  const selection = window.getSelection()
  if (!selection?.rangeCount) return
  const range = selection.getRangeAt(0)
  const rowFor = (node: Node) => (node instanceof HTMLElement ? node : node.parentElement)?.closest<HTMLElement>('[data-paragraph]')
  const row = rowFor(range.startContainer)
  if (!row || !paper.contains(row) || row !== rowFor(range.endContainer)) return
  return { paragraph: Number(row.dataset.paragraph), start: boundary(row, range.startContainer, range.startOffset, false),
    end: boundary(row, range.endContainer, range.endOffset, true) }
}

function Paragraph({ block, index, components, select }: {
  block: Block; index: number; components: Map<string, Component>; select: (s: Selection) => void
}) {
  let pos = 0
  const tokens = block.text.split(/(\{\{\s*[a-z][a-z0-9_]*\s*\}\})/g)
  return <p data-paragraph={index} data-length={length(block.text)} tabIndex={0}
    style={{ textAlign: block.align === 'center' ? 'center' : block.align === 'right' ? 'right' : 'left' }}>
    {tokens.map((token, i) => {
      const start = pos
      pos += length(token)
      const end = pos
      const key = token.match(/^\{\{\s*([a-z][a-z0-9_]*)\s*\}\}$/)?.[1]
      if (!token) return null
      return <span key={i} data-key={key} data-start={start} data-end={end} className={key ? 'field-chip' : undefined}
        onClick={key ? () => {
          if (window.getSelection()?.isCollapsed) select({ paragraph: index, start, end })
        } : undefined}>
        {key ? components.get(key)?.label || key : token}</span>
    })}{!block.text && <br />}</p>
}

type FieldOptions = Pick<Component, 'label' | 'required' | 'question'>

function ComponentForm({ initial, save, cancel }: {
  initial?: Component; save: (data: FieldOptions) => Promise<void>; cancel: () => void
}) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try {
      await save({ label: String(data.get('label')), required: data.has('required'), question: String(data.get('question') || '') })
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  return <form className="component-form" onSubmit={create}>
    <label>Название поля<input name="label" required maxLength={160} defaultValue={initial?.label} autoFocus /></label>
    <label>Вопрос заявителю (необязательно)<input name="question" maxLength={500} defaultValue={initial?.question || ''} /></label>
    <label className="check-field"><input type="checkbox" name="required" defaultChecked={initial?.required ?? true} />Обязательное поле</label>
    {error && <p role="alert">{error}</p>}
    <div className="actions"><button disabled={busy} className="primary">{initial ? 'Применить' : 'Создать'}</button>
      <button disabled={busy} type="button" onClick={cancel}>Отмена</button></div></form>
}

export function TemplateEditor({ initial, close }: { initial: EditorData; close: () => void }) {
  const [title, setTitle] = useState(initial.title)
  const [fields, setFields] = useState(initial.components)
  const [history, setHistory] = useState<Edit[]>([])
  const [cursor, setCursor] = useState(0)
  const [selection, setSelection] = useState<Selection>()
  const [fieldForm, setFieldForm] = useState('')
  const [configured, setConfigured] = useState<Record<string, Component>>({})
  const [replacement, setReplacement] = useState<string>()
  const [preview, setPreview] = useState('')
  const [busy, setBusy] = useState(false)
  const [discard, setDiscard] = useState(false)
  const [error, setError] = useState('')
  const paper = useRef<HTMLDivElement>(null)
  const edits = history.slice(0, cursor)
  const blocks = paragraphs(initial.blocks, edits)
  const components = new Map(fields.map(field => [field.key, configured[field.key] ?? field]))
  const used = new Set(blocks.flatMap(block => Array.from(block.text.matchAll(/\{\{\s*([a-z][a-z0-9_]*)\s*\}\}/g), m => m[1])))
  const prefix = 'templates/' + initial.id
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  function replace(text: string, component?: string) {
    if (!selection) return
    setHistory([...edits, { ...selection, text, component }]); setCursor(cursor + 1)
    setSelection(undefined); setReplacement(undefined); setError('')
    window.getSelection()?.removeAllRanges()
  }
  function move(next: number) {
    setCursor(next); setSelection(undefined); setReplacement(undefined)
  }
  async function submit(action: 'preview' | 'publish') {
    setBusy(true); setError('')
    try {
      const body = post({ title, revision: initial.revision, edits, fields: Object.values(configured) })
      if (action === 'publish') { await api(prefix + '/publish', body); close() }
      else setPreview(URL.createObjectURL(await (await request(prefix + '/preview', body)).blob()))
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  async function saveField(options: FieldOptions) {
    if (fieldForm === 'new') {
      const field = await api<Component>('templates/components', post(options))
      setFields([...fields, field])
    } else {
      setConfigured({ ...configured, [fieldForm]: { ...components.get(fieldForm)!, ...options } })
    }
    setFieldForm('')
  }
  const capture = () => { if (paper.current) setSelection(readSelection(paper.current)) }
  return <main className="template-editor">
    <div className="editor-heading"><button disabled={busy} onClick={() =>
      cursor || title !== initial.title || Object.keys(configured).length ? setDiscard(true) : close()}>← К шаблонам</button>
      <h1>Редактор шаблона</h1><div className="actions">
        <button disabled={busy || !title.trim()} onClick={() => submit('preview')}>Предпросмотр</button>
        <button className="primary" disabled={busy || !title.trim()} onClick={() => submit('publish')}>Сохранить</button>
      </div></div>
    {error && <p role="alert">{error}</p>}
    {discard && <div className="actions" role="alert">Выйти без сохранения?
      <button onClick={close}>Выйти</button><button onClick={() => setDiscard(false)}>Продолжить работу</button></div>}
    <label>Название шаблона<input value={title} maxLength={500} onChange={e => setTitle(e.target.value)} /></label>
    <div className="editor-layout"><section className="editor-document">
      <div className="editor-toolbar">
        <button disabled={!cursor} aria-label="Отменить правку" title="Отменить правку" onClick={() => move(cursor - 1)}>↶</button>
        <button disabled={cursor === history.length} aria-label="Повторить правку" title="Повторить правку" onClick={() => move(cursor + 1)}>↷</button>
        <button disabled={!selection} onClick={() => selection && setReplacement(Array.from(blocks[selection.paragraph].text)
          .slice(selection.start, selection.end).join(''))}>Изменить текст</button>
        <a href={'/api/' + prefix + '/source'} download={initial.filename}>Скачать оригинал</a>
      </div>
      {replacement !== undefined && <div className="editor-toolbar"><input aria-label="Новый текст" maxLength={4000}
        value={replacement} onChange={e => setReplacement(e.target.value)} />
        <button disabled={!selection} onClick={() => replace(replacement)}>Применить</button>
        <button onClick={() => setReplacement(undefined)}>Отмена</button></div>}
      <div className="editor-paper" ref={paper} onPointerUp={capture} onKeyUp={capture}>
        {blocks.map((block, i) => <Paragraph key={i} block={block} index={i} components={components} select={setSelection} />)}
      </div></section>
      <section className="component-panel"><h2>Компоненты</h2>
        <p>Выделите текст в одном абзаце или поставьте курсор в место вставки, затем выберите поле.</p>
        {fieldForm ? <ComponentForm key={fieldForm} initial={components.get(fieldForm)} save={saveField}
          cancel={() => setFieldForm('')} /> : <button onClick={() => setFieldForm('new')}>＋ Создать компонент</button>}
        <div className="component-list">{Array.from(components.values()).map(field => <div className="component-row" key={field.key}>
          <button disabled={!selection}
          onMouseDown={e => e.preventDefault()} onClick={() => replace('', field.key)}>
          <span>{field.label}<small>{field.required ? 'Обязательное' : 'Необязательное'}</small></span><b>＋</b>
        </button>{used.has(field.key) && <button className="configure-field" title="Настроить поле в этом шаблоне"
          aria-label={'Настроить поле «' + field.label + '»'} onClick={() => setFieldForm(field.key)}>⚙</button>}</div>)}</div>
      </section></div>
    {preview && <DocumentPreview url={preview} title={title} close={() => setPreview('')} />}
  </main>
}
