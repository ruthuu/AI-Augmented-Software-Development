import { useState } from 'react'
import { errorMessage, ApiError } from '../../api/client'
import { deleteExpense } from '../../api/expenses'
import type { ConfigResponse, Expense, ExpenseFilters as Filters } from '../../api/types'
import { useExpenses } from '../../hooks/useExpenses'
import { Button } from '../common/Button'
import { EmptyState } from '../common/EmptyState'
import { ErrorBanner } from '../common/ErrorBanner'
import { LoadingIndicator } from '../common/LoadingIndicator'
import { ExpenseFilters } from './ExpenseFilters'
import { ExpenseForm } from './ExpenseForm'
import { ExpenseList } from './ExpenseList'

interface ExpensesSectionProps {
  config: ConfigResponse
  version: number
  onChanged: () => void
}

type FormState = { mode: 'closed' } | { mode: 'add' } | { mode: 'edit'; expense: Expense }

export function ExpensesSection({ config, version, onChanged }: ExpensesSectionProps) {
  const [filters, setFilters] = useState<Filters>({ month: '', category: '' })
  const { expenses, loading, error, reload } = useExpenses(version, filters)
  const filtered = filters.month !== '' || filters.category !== ''
  const noMatch = filtered && !loading && !error && expenses.length === 0
  const [form, setForm] = useState<FormState>({ mode: 'closed' })
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleDelete(expense: Expense) {
    setActionError(null)
    try {
      await deleteExpense(expense.id)
    } catch (failure) {
      setActionError(errorMessage(failure))
      if (!(failure instanceof ApiError) || failure.status !== 404) {
        return
      }
    }
    onChanged()
  }

  function handleSaved() {
    setForm({ mode: 'closed' })
    onChanged()
  }

  return (
    <section className="section" aria-labelledby="expenses-heading">
      <div className="toolbar">
        <h2 id="expenses-heading">Expenses</h2>
        <Button variant="primary" onClick={() => setForm({ mode: 'add' })}>
          Add expense
        </Button>
      </div>
      {actionError ? <ErrorBanner message={actionError} /> : null}
      <ExpenseFilters config={config} filters={filters} onChange={setFilters} showClear={!noMatch} />
      {error ? <ErrorBanner message={error} onRetry={reload} /> : null}
      {loading ? <LoadingIndicator /> : null}
      {noMatch ? (
        <EmptyState message="No expenses match these filters">
          <Button onClick={() => setFilters({ month: '', category: '' })}>Clear filters</Button>
        </EmptyState>
      ) : null}
      {!filtered && !error && !loading && expenses.length === 0 ? (
        <EmptyState message="No expenses yet. Add your first expense." />
      ) : null}
      {expenses.length > 0 ? (
        <ExpenseList
          expenses={expenses}
          onEdit={(expense) => setForm({ mode: 'edit', expense })}
          onDelete={handleDelete}
        />
      ) : null}
      {form.mode !== 'closed' ? (
        <ExpenseForm
          config={config}
          expense={form.mode === 'edit' ? form.expense : null}
          onSaved={handleSaved}
          onCancel={() => setForm({ mode: 'closed' })}
          onStale={onChanged}
        />
      ) : null}
    </section>
  )
}
