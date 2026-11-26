import { type ReactNode } from 'react'

const emphasis = /\\([\\*])|(?<!\*)\*\*((?:\\[\\*]|[^*\r\n])+?)\*\*(?!\*)|(?<!\*)\*((?:\\[\\*]|[^*\r\n])+?)\*(?!\*)/g

function unescape(text: string) {
  return text.replace(/\\([\\*])/g, '$1')
}

export function MarkdownText({ text }: { text: string }) {
  const parts: ReactNode[] = []
  let end = 0

  for (const match of text.matchAll(emphasis)) {
    const start = match.index
    const [source, escaped, bold, italic] = match
    parts.push(text.slice(end, start))
    if (escaped) parts.push(escaped)
    else if (bold?.trim()) parts.push(<strong key={start}>{unescape(bold)}</strong>)
    else if (italic?.trim()) parts.push(<em key={start}>{unescape(italic)}</em>)
    else parts.push(source)
    end = start + source.length
  }

  parts.push(text.slice(end))
  return <p className="markdown-text">{parts}</p>
}
