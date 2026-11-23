import type { ApiErrorBody, InterpretResponse } from './types.ts'

const pad = (n: number) => String(n).padStart(2, '0')

// ISO 8601 with the browser's UTC offset, so the backend resolves "tomorrow" in the user's zone.
export function localIsoNow(d: Date = new Date()): string {
  const offset = -d.getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  const abs = Math.abs(offset)
  const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  return `${date}T${time}${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
}

export async function interpret(text: string): Promise<InterpretResponse> {
  let response: Response
  try {
    response = await fetch('/api/interpret', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, now: localIsoNow() }),
    })
  } catch {
    throw new Error('Could not reach the server. Is the backend running?')
  }

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new Error(`Unexpected response from the server (HTTP ${response.status}).`)
  }

  if (!response.ok) {
    const message = (body as Partial<ApiErrorBody>).error?.message
    throw new Error(message ?? `Request failed (HTTP ${response.status}).`)
  }
  return body as InterpretResponse
}
