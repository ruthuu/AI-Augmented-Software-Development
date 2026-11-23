import type { Summary } from '../../api/types'
import { formatMoney } from '../../utils/formatMoney'
import { EmptyState } from '../common/EmptyState'

interface CategoryBreakdownProps {
  summary: Summary
}

export function CategoryBreakdown({ summary }: CategoryBreakdownProps) {
  return (
    <div className="category-breakdown">
      <h3>Spending by category</h3>
      {summary.by_category.length === 0 ? (
        <EmptyState message="No expenses recorded this month" />
      ) : (
        <ul className="breakdown">
          {summary.by_category.map((row) => (
            <li key={row.category}>
              <span>{row.category}</span>
              <span>{formatMoney(row.total)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}