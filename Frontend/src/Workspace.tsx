import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, post, roles, stream, type Account, type Chat, type Turn } from './api'
import { Brand } from './Brand'
import { Management } from './Management'
export function Workspace({ account, signedOut }: { account: Account; signedOut: () => void }) {
  const [sidebar, setSidebar] = useState(false)
  const [page, setPage] = useState<'chat' | 'accounts'>('chat')
  const [chats, setChats] = useState<Chat[]>([])
  const [id, setId] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
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

  async function open(chatId: string) {
    setBusy(true)
    setError('')
    try {
      const history = chatId ? await api<Turn[]>(`chats/${chatId}/messages`) : []
      setTurns(history); setId(chatId); setPage('chat'); setDraft('')
      if (window.innerWidth < 760) setSidebar(false)
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  async function removeChat(chat: Chat) {
    if (busy || !window.confirm(`Удалить чат «${chat.title}»?`)) return
    setBusy(true)
    setError('')
    try {
      await api(`chats/${chat.id}`, { method: 'DELETE' })
      setChats(current => current.filter(item => item.id !== chat.id))
      if (id === chat.id) {
        setId('')
        setTurns([])
        setDraft('')
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
      await stream(chatId, question, token => {
        answer += token
        setPending({ question, answer })
      }, controller.signal)
      setTurns(await api<Turn[]>(`chats/${chatId}/messages`))
    } catch (e) { setError((e as Error).message); setDraft(question) }
    finally {
      setPending(null); active.current = null
      await refresh().catch(e => setError(e.message))
      setBusy(false)
    }
  }

  return <div className="shell"><header>
    <button className="menu" aria-label="История чатов" aria-expanded={sidebar} onClick={() => setSidebar(!sidebar)}>☰</button><Brand />
    <div className="profile"><span className="avatar" aria-hidden="true">{Array.from(account.name)[0]?.toUpperCase()}</span><span>{account.name}<small>{roles[account.role]}</small></span>
      <button onClick={() => api('auth/logout', post()).then(signedOut).catch(e => setError(e.message))}>Выйти</button></div></header>
    <div className="layout">{sidebar && <aside><button className="new" disabled={busy} onClick={() => open('')}>＋ Новый чат</button>
      <h2>История</h2><nav>{chats.map(c => <div className="history-item" key={c.id}>
        <button disabled={busy} className={id === c.id ? 'selected' : ''} onClick={() => open(c.id)}>{c.title}</button>
        <button className="delete-chat" disabled={busy} aria-label={`Удалить чат «${c.title}»`}
          title="Удалить чат" onClick={() => removeChat(c)}>×</button>
      </div>)}</nav>
      <div className="tools">
        {account.role === 'Admin' && <button disabled={busy} onClick={() => {setPage('accounts'); setSidebar(false)}}>Пользователи</button>}</div></aside>}
      {page !== 'chat' ? <Management account={account} back={() => setPage('chat')} /> :
        <main className="chat"><section className="conversation">
        {!turns.length && !pending ? <div className="greeting"><Brand /><h1>Чем могу помочь, <em>{account.name}</em>?</h1></div> :
          <div className="thread">{[...turns, ...(pending ? [pending] : [])].map((t, i) =>
          <article key={i}><div className="question">{t.question}</div><div className="answer">
            {t.answer && <p>{t.answer}</p>}
            {t === pending && <div className="loading" role="status">
              <span className="spinner" aria-hidden="true" />
              {t.answer ? 'Продолжаю ответ…' : 'Думаю…'}
            </div>}
          </div></article>)}<div ref={end} /></div>}
        </section><div className="compose">{error && <p role="alert">{error}</p>}
          <form onSubmit={send}><textarea aria-label="Сообщение" value={draft} maxLength={4000}
            placeholder="Напишите сообщение…" rows={2}
            onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} />
            <div className="compose-controls">
              <button className="send" disabled={busy || !draft.trim()} aria-label="Отправить сообщение">↑</button>
            </div>
          </form></div></main>}
    </div></div>
}
