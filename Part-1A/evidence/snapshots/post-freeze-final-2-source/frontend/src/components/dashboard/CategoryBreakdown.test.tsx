import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeSummary } from '../../test/fixtures'
import { CategoryBreakdown } from './CategoryBreakdown'

describe('CategoryBreakdown', () => {
  it('lists each category with its total in the given order', () => {
    render(
      <CategoryBreakdown
        summary={makeSummary({
          total_spent: '350.30',
          expense_count: 3,
          by_category: [
            { category: 'Food', total: '300.30', count: 2 },
            { category: 'Transport', total: '50.00', count: 1 },
          ],
        })}
      />,
    )
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('Food')
    expect(items[0]).toHaveTextContent('₹300.30')
    expect(items[1]).toHaveTextContent('Transport')
    expect(items[1]).toHaveTextContent('₹50.00')
    expect(screen.queryByText('No expenses recorded this month')).not.toBeInTheDocument()
  })

  it('does not list a category without spending', () => {
    render(
      <CategoryBreakdown
        summary={makeSummary({ by_category: [{ category: 'Food', total: '10.00', count: 1 }] })}
      />,
    )
    expect(screen.queryByText('Bills')).not.toBeInTheDocument()
  })

  it('shows a message instead of rows when the month has no expenses', () => {
    render(<CategoryBreakdown summary={makeSummary()} />)
    expect(screen.getByText('No expenses recorded this month')).toBeInTheDocument()
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
  })
})
