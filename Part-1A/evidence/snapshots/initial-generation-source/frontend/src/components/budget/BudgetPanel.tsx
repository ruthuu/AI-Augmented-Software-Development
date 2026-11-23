import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, errorMessage } from '../../api/client'
import { saveBudget } from '../../api/budgets'
import type { Summary } from '../../api/types'
import { formatMoney } from '../../utils/formatMoney'
import { Button } from '../common/Button'
import { ErrorBanner } from '../common/ErrorBanner'
import { FormField } from '../common/FormField'
import { OverBudgetAlert } from './OverBudgetAlert'

interface BudgetPanelProps {
  month: string
  summary: Summary | null
  onSaved: () => void
}

export function BudgetPanel({ month, summary, onSaved }: BudgetPanelProps) {
  const [amount, setAmount] = useState(summary?.budget?.amount ?? '')
  const [fieldError, setFieldError] = useState<string | undefined>(undefined)
  const [banner, setBanner] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const pendingRef = useRef(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pendingRef.current) {
      return
    }
    pendingRef.current = true
    setPending(true)
    setFieldError(undefined)
    setBanner(null)
    try {
      await saveBudget(month, amount)
      onSaved()
    } catch (failure) {
      const message = failure instanceof ApiError ? failure.fieldMessage('amount') : undefined
      if (message) {
        setFieldError(message)
      } else {
        setBanner(errorMessage(failure))
      }
    } finally {
      pendingRef.current = false
      setPending(false)
    }
  }

  return (
    <div className="budget-panel">
      <form className="budget-form" onSubmit={handleSubmit} noValidate>
        <FormField
          id="budget-amount"
          label="Budget"
          inputMode="decimal"
          autoComplete="off"
          value={amount}
          error={fieldError}
          onChange={(event) => setAmount(event.target.value)}
        />
        <Button type="submit" variant="primary" disabled={pending}>
          Save budget
        </Button>
      </form>
      {banner ? <ErrorBanner message={banner} /> : null}
      {summary ? (
        <>
          <dl className="figures">
            <div>
              <dt>Spent</dt>
              <dd>{formatMoney(summary.total_spent)}</dd>
            </div>
            {summary.remaining !== null ? (
              <div>
                <dt>Remaining</dt>
                <dd>{formatMoney(summary.remaining)}</dd>
              </div>
            ) : null}
          </dl>
          {summary.budget === null ? <p className="muted">No budget set for this month</p> : null}
          <OverBudgetAlert overBy={summary.over_budget ? summary.over_budget_by : null} />
        </>
      ) : null}
    </div>
  )
}
