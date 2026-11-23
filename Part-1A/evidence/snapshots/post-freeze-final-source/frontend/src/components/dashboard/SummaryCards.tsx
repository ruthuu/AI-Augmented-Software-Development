import type { Summary } from '../../api/types'
import { formatMoney } from '../../utils/formatMoney'

interface SummaryCardsProps {
  summary: Summary
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  return (
    <div className="cards">
      <div className="card">
        <span className="label">Total spent</span>
        <span className="value">{formatMoney(summary.total_spent)}</span>
      </div>
      <div className="card">
        <span className="label">Expenses this month</span>
        <span className="value">{summary.expense_count}</span>
      </div>
      <div className="card">
        <span className="label">All-time expenses</span>
        <span className="value">{summary.total_recorded_count}</span>
      </div>
    </div>
  )
}