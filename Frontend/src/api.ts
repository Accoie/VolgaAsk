export type Role = 'User' | 'Employee' | 'Admin'
export type Account = { id: string; login: string; name: string; role: Role }
export type Chat = { id: string; title: string; updatedAt: string }
export type Turn = { question: string; answer: string; fileId?: string; documentTitle?: string;
  preview?: string; report?: string; awaitingConfirmation?: boolean }
export const roles: Record<Role, string> = { User: 'Пользователь', Employee: 'Сотрудник', Admin: 'Администратор' }

export function post(body?: unknown): RequestInit {
  return body === undefined ? { method: 'POST' } : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  }
}

export async function request(path: string, options?: RequestInit) {
  const response = await fetch('/api/' + path, options)
  if (response.ok) return response
  if (response.status === 401 && path !== 'auth/login') window.dispatchEvent(new Event('session-expired'))
  const fallback: Record<number, string> = {
    400: 'Проверьте введённые данные.', 401: 'Проверьте логин и пароль.', 403: 'Недостаточно прав.',
    404: 'Запись не найдена.', 409: 'Действие уже выполняется.', 429: 'Слишком много попыток входа.'
  }
  const message = response.headers.get('content-type')?.startsWith('text/plain') && await response.text()
  throw new Error(message || fallback[response.status] || 'Сервис временно недоступен.')
}

export function api<T = void>(path: string, options?: RequestInit): Promise<T>
export async function api(path: string, options?: RequestInit): Promise<unknown> {
  const response = await request(path, options)
  const text = await response.text()
  return text ? JSON.parse(text) : undefined
}

export async function stream(id: string, input: { question: string; mode: string; reviseFile?: string },
  token: (s: string) => void, status: (s: string) => void, signal: AbortSignal) {
  const response = await request(`chats/${id}/messages`, { ...post(input), signal })
  const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader()
  let pending = ''
  try {
    while (true) {
      const chunk = await reader.read()
      if (chunk.done) throw new Error('Соединение прервано до завершения ответа.')
      pending += chunk.value
      let end: number
      while ((end = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, end).trimEnd()
        pending = pending.slice(end + 1)
        if (!line.startsWith('data: ')) continue
        const event = JSON.parse(line.slice(6))
        if (event.type === 'done') return
        if (event.type === 'error') throw new Error(event.text)
        if (event.type === 'token') token(event.text)
        if (event.type === 'status') status(event.text)
      }
    }
  } finally {
    reader.releaseLock()
  }
}
