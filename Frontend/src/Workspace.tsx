import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { api, post, roles, stream, type Account, type Chat, type Turn } from './api'
import { Brand } from './Brand'
import { Management } from './Management'
import { DocumentManagement } from './DocumentManagement'
import { DocumentCard } from './DocumentCard'
import { MarkdownText } from './MarkdownText'
import questionIcon from './assets/baffled.png'
import documentIcon from './assets/ai-document.png'
import managementIcon from './assets/management.png'
import logoutIcon from './assets/quit.png'

const modes = [
  { value: 'auto', label: 'Автоматически', icon: '✦' },
  { value: 'question', label: 'Вопрос об университете', icon: '?' },
  { value: 'document', label: 'Оформление документа', icon: '▤' },
]

export function Workspace({ account, signedOut, themeToggle }: {
  account: Account; signedOut: () => void; themeToggle: ReactNode
}) {
  const [sidebar, setSidebar] = useState(false)
  const [page, setPage] = useState<'chat' | 'accounts' | 'kb'>('chat')
  const [chats, setChats] = useState<Chat[]>([])
  const [deleteTarget, setDeleteTarget] = useState<Chat | null>(null)
  const deleteDialog = useRef<HTMLDialogElement>(null)
  const [id, setId] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [mode, setMode] = useState('auto')
  const [revision, setRevision] = useState<Turn | null>(null)
  const [status, setStatus] = useState('')
  const composer = useRef<HTMLTextAreaElement>(null)
  const [pending, setPending] = useState<Turn | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  const active = useRef<AbortController | null>(null)
  const refresh = () => api<Chat[]>('chats').then(setChats)
  useEffect(() => {
    refresh().catch(e => setError(e.message))
    return () => active.current?.abort()
  }, [])
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [turns, pending])
  useEffect(() => {
    if (deleteTarget && !deleteDialog.current?.open) deleteDialog.current?.showModal()
  }, [deleteTarget])

  async function open(chatId: string) {
    setBusy(true)
    setError('')
    try {
      const history = chatId ? await api<Turn[]>(`chats/${chatId}/messages`) : []
      setTurns(history); setId(chatId); setPage('chat'); setDraft('')
      setRevision(null); setMode('auto')
      if (window.innerWidth < 760) setSidebar(false)
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  async function removeChat(chat: Chat) {
    if (busy) return
    deleteDialog.current?.close()
    setBusy(true)
    setError('')
    try {
      await api(`chats/${chat.id}`, { method: 'DELETE' })
      setChats(current => current.filter(item => item.id !== chat.id))
      if (id === chat.id) {
        setId('')
        setTurns([])
        setDraft('')
        setRevision(null); setMode('auto')
      }
      setPage('chat')
    } catch (e) {
      setPage('chat')
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault()
    const question = draft.trim()
    if (!question || busy) return
    setBusy(true); setError(''); setDraft(''); setPending({ question, answer: '' })
    const controller = new AbortController()
    active.current = controller
    let answer = ''
    try {
      const chatId = id || (await api<Chat>('chats', post())).id
      setId(chatId)
      await stream(chatId, { question, mode, reviseFile: revision?.fileId }, token => {
        answer += token
        setPending({ question, answer })
      }, setStatus, controller.signal)
      setTurns(await api<Turn[]>(`chats/${chatId}/messages`))
      setRevision(null); setMode('auto')
    } catch (e) { setError((e as Error).message); setDraft(question) }
    finally {
      setStatus(''); setPending(null); active.current = null
      await refresh().catch(e => setError(e.message))
      setBusy(false)
    }
  }

  return <div className="shell"><header>
    <button className="menu" aria-label="История чатов" aria-expanded={sidebar} onClick={() => setSidebar(!sidebar)}>☰</button><Brand showEmblem />
    <div className="header-user-controls">
      <div className="profile">
        <div className="profile-user"><span className="avatar" aria-hidden="true">{Array.from(account.name)[0]?.toUpperCase()}</span>
          <span>{account.name}<small>{roles[account.role]}</small></span></div>
        <button className="logout-button" aria-label="Выйти" title="Выйти"
          onClick={() => api('auth/logout', post()).then(signedOut).catch(e => setError(e.message))}>
          <img src={logoutIcon} alt="" />
        </button>
      </div>
      {themeToggle}
    </div></header>
    <div className="layout">{sidebar && <aside><button className="new" disabled={busy} onClick={() => open('')}>＋ Новый чат</button>
      <h2>История</h2><nav>{chats.map(c => <div className="history-item" key={c.id}>
        <button disabled={busy} className={id === c.id ? 'selected' : ''} onClick={() => open(c.id)}>{c.title}</button>
        <button className="delete-chat" disabled={busy} aria-label={`Удалить чат «${c.title}»`}
          title="Удалить чат" onClick={() => setDeleteTarget(c)}>×</button>
      </div>)}</nav>
      <div className="tools">
        {account.role !== 'User' && <button className="management-link" disabled={busy}
          onClick={() => {setPage('kb'); setSidebar(false)}}>
          <img src={managementIcon} alt="" />Управление
        </button>}
        {account.role === 'Admin' && <button disabled={busy} onClick={() => {setPage('accounts'); setSidebar(false)}}>Пользователи</button>}</div></aside>}
      {page === 'kb' ? <DocumentManagement back={() => setPage('chat')} /> :
        page === 'accounts' ? <Management account={account} back={() => setPage('chat')} /> :
        <main className="chat" onClick={sidebar ? () => setSidebar(false) : undefined}><section className="conversation">
        {!turns.length && !pending ? <div className="greeting"><Brand /><h1>Чем могу помочь, <em>{account.name}</em>?</h1>
          <div className="actions">{[
            { value: 'document', label: 'Создать документ', icon: documentIcon },
            { value: 'question', label: 'Задать вопрос', icon: questionIcon },
          ].map(({ value, label, icon }) =>
            <button key={value} onClick={() => { setMode(value); composer.current?.focus() }}>
              <img className="greeting-action-icon" src={icon} alt="" />{label}
            </button>)}</div></div> :
          <div className="thread">{[...turns, ...(pending ? [pending] : [])].map((t, i) =>
          <article key={i}><div className="question">{t.question}</div><div className="answer">
            {t.answer && <MarkdownText text={t.answer} />}
            {t === pending && <div className="loading" role="status">
              <span className="spinner" aria-hidden="true" />
              {status || (t.answer ? 'Продолжаю ответ…' : 'Думаю…')}
            </div>}
            {t.fileId && <DocumentCard chatId={id} turn={t} busy={busy} revise={() => {
              setRevision(t); setMode('document'); composer.current?.focus()
            }} />}
          </div></article>)}<div ref={end} /></div>}
        </section><div className="compose-area"><div className="compose">{error && <p role="alert">{error}</p>}
          <form onSubmit={send}>
            {revision && <small>Доработка · {revision.documentTitle}</small>}
            <textarea ref={composer} aria-label="Сообщение" value={draft} maxLength={4000}
            placeholder={revision ? 'Что нужно исправить в документе?' : 'Напишите сообщение…'} rows={2}
            onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} />
            <div className="compose-controls">
              <div className="mode-buttons" role="group" aria-label="Режим сообщения">
                {modes.map(({ value, label, icon }) => <button type="button" key={value} disabled={busy}
                  title={label} aria-label={label} aria-pressed={mode === value}
                  onClick={() => { setMode(value); setRevision(null); composer.current?.focus() }}>{icon}</button>)}
              </div>
              <button className="send" disabled={busy || !draft.trim()} aria-label="Отправить сообщение">↑</button>
            </div>
          </form></div></div></main>}
    </div>
    <dialog className="delete-dialog" ref={deleteDialog} aria-labelledby="delete-chat-title"
      aria-describedby="delete-chat-description" onClose={() => setDeleteTarget(null)}>
      <h2 id="delete-chat-title">Удалить чат?</h2>
      <p id="delete-chat-description">«{deleteTarget?.title}» исчезнет из истории.</p>
      <form method="dialog" className="actions">
        <button autoFocus>Отмена</button>
        <button type="button" className="danger" disabled={busy}
          onClick={() => { if (deleteTarget) void removeChat(deleteTarget) }}>Удалить</button>
      </form>
    </dialog>
  </div>
}
