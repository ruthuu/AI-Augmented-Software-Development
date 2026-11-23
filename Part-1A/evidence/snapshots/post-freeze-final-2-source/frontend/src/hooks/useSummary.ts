import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '../api/client'
import { getSummary } from '../api/summary'
import type { Summary } from '../api/types'

interface Outcome {
  key: string
  summary?: Summary
  error?: string
}

// Refetches whenever `version` or the month changes; the last good summary stays visible meanwhile.
export function useSummary(month: string, version: number) {
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [lastGood, setLastGood] = useState<Summary | null>(null)
  const [reloads, setReloads] = useState(0)
  const key = `${version}:${reloads}:${month}`

  useEffect(() => {
    let cancelled = false
    getSummary(month)
      .then((summary) => {
        if (cancelled) return
        setLastGood(summary)
        setOutcome({ key, summary })
      })
      .catch((failure: unknown) => {
        if (!cancelled) setOutcome({ key, error: errorMessage(failure) })
      })
    return () => {
      cancelled = true
    }
  }, [key, month])

  const current = outcome?.key === key ? outcome : null
  const reload = useCallback(() => setReloads((count) => count + 1), [])
  return {
    summary: current?.summary ?? (lastGood?.month === month ? lastGood : null),
    loading: current === null,
    error: current?.error ?? null,
    reload,
  }
}
