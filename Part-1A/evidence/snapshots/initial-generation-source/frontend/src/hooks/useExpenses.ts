import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '../api/client'
import { listExpenses } from '../api/expenses'
import type { Expense, ExpenseFilters } from '../api/types'

interface Outcome {
  key: string
  expenses?: Expense[]
  error?: string
}

// Refetches whenever `version` or a filter changes; the last good list stays visible meanwhile.
export function useExpenses(version: number, filters: ExpenseFilters) {
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [lastGood, setLastGood] = useState<Expense[]>([])
  const [reloads, setReloads] = useState(0)
  const { month, category } = filters
  const key = `${version}:${reloads}:${month}:${category}`

  useEffect(() => {
    let cancelled = false
    listExpenses({ month, category })
      .then((expenses) => {
        if (cancelled) return
        setLastGood(expenses)
        setOutcome({ key, expenses })
      })
      .catch((failure: unknown) => {
        if (!cancelled) setOutcome({ key, error: errorMessage(failure) })
      })
    return () => {
      cancelled = true
    }
  }, [key, month, category])

  const current = outcome?.key === key ? outcome : null
  const reload = useCallback(() => setReloads((count) => count + 1), [])
  return {
    expenses: current?.expenses ?? lastGood,
    loading: current === null,
    error: current?.error ?? null,
    reload,
  }
}