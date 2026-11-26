import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { api, post, type Account } from './api'
import { Workspace } from './Workspace'
import { Brand } from './Brand'
import './styles.css'
import './theme.css'

function Login({ signedIn, themeToggle }: { signedIn: (account: Account) => void; themeToggle: ReactNode }) {
  const [register, setRegister] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = Object.fromEntries(new FormData(e.currentTarget))
      signedIn(await api<Account>(register ? 'auth/register' : 'auth/login', post(data)))
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  return <div className="shell"><header><Brand showEmblem />{themeToggle}</header><main className="login">
    <form className="card" onSubmit={submit}><h1>{register ? 'Регистрация' : 'Вход в чат'}</h1>
      <label>Логин<input autoFocus name="login" maxLength={64} required autoComplete="username" /></label>
      {register && <label>Имя<input name="name" required maxLength={80} autoComplete="given-name" /></label>}
      <label>Пароль<input name="password" type="password" required minLength={register ? 10 : undefined} maxLength={128} autoComplete={register ? 'new-password' : 'current-password'} /></label>
      {error && <p role="alert">{error}</p>}<button className="primary" disabled={busy}>{register ? 'Зарегистрироваться' : 'Войти'}</button>
      <button type="button" disabled={busy} onClick={() => { setRegister(!register); setError('') }}>
        {register ? 'Уже есть аккаунт? Войти' : 'Создать аккаунт'}
      </button>
    </form></main></div>
}

function App() {
  const [account, setAccount] = useState<Account | null>()
  const [dark, setDark] = useState(() => localStorage.getItem('volgaask.theme') === 'dark')
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    localStorage.setItem('volgaask.theme', dark ? 'dark' : 'light')
  }, [dark])
  useEffect(() => {
    const expire = () => setAccount(null)
    window.addEventListener('session-expired', expire)
    api<Account>('auth/me').then(setAccount).catch(expire)
    return () => window.removeEventListener('session-expired', expire)
  }, [])
  if (account === undefined) return <main className="login">Загрузка…</main>
  const themeLabel = dark ? 'Включить светлую тему' : 'Включить тёмную тему'
  const themeToggle = <button type="button" className="theme-toggle" aria-label={themeLabel} title={themeLabel}
    onClick={() => setDark(value => !value)}><span aria-hidden="true">{dark ? '☀' : '☾'}</span></button>
  return account ? <Workspace account={account} signedOut={() => setAccount(null)} themeToggle={themeToggle} />
    : <Login signedIn={setAccount} themeToggle={themeToggle} />
}

createRoot(document.getElementById('root')!).render(<App />)
