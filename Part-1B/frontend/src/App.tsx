import { useState } from 'react'
import type { FormEvent } from 'react'
import { interpret } from './api.ts'
import type { InterpretResponse } from './types.ts'

const MAX_LENGTH = 500

function formatWhen(iso: string): string {
  return `${new Date(iso).toLocaleString()} (${iso})`
}

function Result({ data }: { data: InterpretResponse }) {
  const { result } = data
  return (
    <section aria-label="Result">
      <h2>Intent: {result.intent}</h2>
      <dl>
        {result.title && (
          <>
            <dt>Reminder</dt>
            <dd>{result.title}</dd>
          </>
        )}
        {result.reminder_reference && (
          <>
            <dt>Reminder to reschedule</dt>
            <dd>{result.reminder_reference}</dd>
          </>
        )}
        {result.scheduled_at && (
          <>
            <dt>{result.intent === 'RESCHEDULE' ? 'New date and time' : 'Date and time'}</dt>
            <dd>{formatWhen(result.scheduled_at)}</dd>
          </>
        )}
        {result.clarification && (
          <>
            <dt>Clarification needed</dt>
            <dd>{result.clarification}</dd>
          </>
        )}
      </dl>
      {data.persisted === false && (
        <p role="status">
          <strong>NOT SAVED (persisted: false).</strong> {data.note}
        </p>
      )}
    </section>
  )
}

export default function App() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<InterpretResponse | null>(null)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setData(null)
    try {
      setData(await interpret(text))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Reminder Agent</h1>
      <p>Interprets a reminder request. It does not save, schedule or change any reminder.</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="request">Your request</label>
        <textarea
          id="request"
          rows={4}
          maxLength={MAX_LENGTH}
          style={{ display: 'block', width: '100%', boxSizing: 'border-box' }}
          placeholder="Remind me to call mom tomorrow at 6pm"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" disabled={loading || text.trim() === ''}>
          {loading ? 'Interpreting…' : 'Interpret request'}
        </button>
      </form>
      {loading && <p role="status">Waiting for the agent…</p>}
      {error && <p role="alert">Error: {error}</p>}
      {data && <Result data={data} />}
    </main>
  )
}
