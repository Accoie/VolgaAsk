import { useEffect, useState, type FormEvent } from 'react'
import { api, post, roles, type Account, type Role } from './api'

type Props = { account: Account; back: () => void }

export function Management({ account, back }: Props) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => api<Account[]>('accounts').then(setAccounts)
  useEffect(() => { load().catch(e => setError(e.message)) }, [])

  async function change(action: () => Promise<unknown>) {
    setBusy(true); setError('')
    try { await action(); await load() }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    change(async () => {
      await api('accounts', post(Object.fromEntries(data)))
      form.reset()
    })
  }

  const options = Object.entries(roles).map(([r, name]) => <option value={r} key={r}>{name}</option>)
  return <main className="management"><button onClick={back}>← К чату</button><h1>Пользователи</h1>
    <form onSubmit={submit}>
      <label>Логин<input name="login" maxLength={64} required /></label>
      <label>Имя<input name="name" required maxLength={80} /></label>
      <label>Пароль<input name="password" type="password" required minLength={10} maxLength={128} autoComplete="new-password" /></label>
      <label>Роль<select name="role">{options}</select></label>
      <button className="primary" disabled={busy}>{busy ? 'Обработка…' : 'Создать'}</button></form>
    {error && <p role="alert">{error}</p>}
    {accounts.map(a => <div className="row" key={a.id}><span>{a.name}<small>{a.login}</small></span><select aria-label={'Роль ' + a.login} value={a.role}
        disabled={busy || a.id === account.id} onChange={e => {
          const role = e.target.value as Role
          change(() => api('accounts/' + a.id + '/role', { ...post({ role }), method: 'PUT' }))
        }}>{options}</select></div>)}</main>
}
