import { useState } from 'react'
import type { Expense } from '../../api/types'
import { formatDate } from '../../utils/formatDate'
import { formatMoney } from '../../utils/formatMoney'
import { Button } from '../common/Button'
import { ConfirmDialog } from '../common/ConfirmDialog'

interface ExpenseRowProps {
  expense: Expense
  onEdit: (expense: Expense) => void
  onDelete: (expense: Expense) => void
}

export function ExpenseRow({ expense, onEdit, onDelete }: ExpenseRowProps) {
  const [confirming, setConfirming] = useState(false)

  return (
    <li className="expense-row">
      <span className="date">{formatDate(expense.expense_date)}</span>
      <span className="description">{expense.description}</span>
      <span className="category">{expense.category}</span>
      <span className="payment">{expense.payment_method}</span>
      <span className="amount">{formatMoney(expense.amount)}</span>
      <span className="row-actions">
        <Button onClick={() => onEdit(expense)} aria-label={`Edit ${expense.description}`}>
          Edit
        </Button>
        <Button onClick={() => setConfirming(true)} aria-label={`Delete ${expense.description}`}>
          Delete
        </Button>
      </span>
      {confirming ? (
        <ConfirmDialog
          title="Delete expense"
          message={`Delete "${expense.description}" for ${formatMoney(expense.amount)}? This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={() => {
            setConfirming(false)
            onDelete(expense)
          }}
          onCancel={() => setConfirming(false)}
        />
      ) : null}
    </li>
  )
}
