import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, errorMessage } from '../../api/client'
import { createExpense, updateExpense } from '../../api/expenses'
import type { ConfigResponse, Expense, ExpenseInput } from '../../api/types'
import { Button } from '../common/Button'
import { ErrorBanner } from '../common/ErrorBanner'
import { FormField } from '../common/FormField'
import { LoadingIndicator } from '../common/LoadingIndicator'
import { ModalPanel } from '../common/ModalPanel'
import { SelectField } from '../common/SelectField'

interface ExpenseFormProps {
  config: ConfigResponse
  expense: Expense | null
  onSaved: () => void
  onCancel: () => void
  onStale?: () => void
}

const FIELDS: (keyof ExpenseInput)[] = ['amount', 'description', 'category', 'payment_method', 'expense_date']

function initialValues(expense: Expense | null): ExpenseInput {
  return {
    amount: expense?.amount ?? '',
    description: expense?.description ?? '',
    category: expense?.category ?? '',
    payment_method: expense?.payment_method ?? '',
    expense_date: expense?.expense_date ?? '',
  }
}

export function ExpenseForm({ config, expense, onSaved, onCancel, onStale }: ExpenseFormProps) {
  const [values, setValues] = useState<ExpenseInput>(() => initialValues(expense))
  const [errors, setErrors] = useState<Partial<Record<keyof ExpenseInput, string>>>({})
  const [banner, setBanner] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const pendingRef = useRef(false)

  function change(field: keyof ExpenseInput, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function showFailure(failure: unknown) {
    if (failure instanceof ApiError && failure.errors.length > 0) {
      const mapped: Partial<Record<keyof ExpenseInput, string>> = {}
      let unmatched: string | null = null
      for (const error of failure.errors) {
        if ((FIELDS as string[]).includes(error.field)) {
          mapped[error.field as keyof ExpenseInput] = error.message
        } else {
          unmatched = error.message
        }
      }
      setErrors(mapped)
      setBanner(unmatched)
      return
    }
    setBanner(errorMessage(failure))
    if (failure instanceof ApiError && failure.status === 404) {
      onStale?.()
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pendingRef.current) {
      return
    }
    pendingRef.current = true
    setPending(true)
    setErrors({})
    setBanner(null)
    try {
      if (expense) {
        await updateExpense(expense.id, values)
      } else {
        await createExpense(values)
      }
      onSaved()
    } catch (failure) {
      showFailure(failure)
    } finally {
      pendingRef.current = false
      setPending(false)
    }
  }

  return (
    <ModalPanel title={expense ? 'Edit expense' : 'Add expense'} onClose={onCancel}>
      <form onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <FormField
            id="expense-amount"
            label="Amount"
            inputMode="decimal"
            autoComplete="off"
            value={values.amount}
            error={errors.amount}
            onChange={(event) => change('amount', event.target.value)}
          />
          <FormField
            id="expense-description"
            label="Description"
            autoComplete="off"
            value={values.description}
            error={errors.description}
            onChange={(event) => change('description', event.target.value)}
          />
          <SelectField
            id="expense-category"
            label="Category"
            placeholder="Select a category"
            options={config.categories}
            value={values.category}
            error={errors.category}
            onChange={(event) => change('category', event.target.value)}
          />
          <SelectField
            id="expense-payment-method"
            label="Payment method"
            placeholder="Select a payment method"
            options={config.payment_methods}
            value={values.payment_method}
            error={errors.payment_method}
            onChange={(event) => change('payment_method', event.target.value)}
          />
          <FormField
            id="expense-date"
            label="Date"
            type="date"
            min={config.limits.min_date}
            max={config.today}
            value={values.expense_date}
            error={errors.expense_date}
            onChange={(event) => change('expense_date', event.target.value)}
          />
        </div>
        {banner ? <ErrorBanner message={banner} /> : null}
        {pending ? <LoadingIndicator label="Saving" /> : null}
        <div className="modal-actions">
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={pending}>
            Save
          </Button>
        </div>
      </form>
    </ModalPanel>
  )
}
