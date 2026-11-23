import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeSummary } from '../../test/fixtures'
import { SummaryCards } from './SummaryCards'

describe('SummaryCards', () => {
  it('shows total spending, the month count, and the all-time count', () => {
    render(
      <SummaryCards
        summary={makeSummary({ total_spent: '350.30', expense_count: 3, total_recorded_count: 57 })}
      />,
    )
    const total = screen.getByText('Total spent').closest('div') as HTMLElement
    expect(within(total).getByText('₹350.30')).toBeInTheDocument()
    const month = screen.getByText('Expenses this month').closest('div') as HTMLElement
    expect(within(month).getByText('3')).toBeInTheDocument()
    const allTime = screen.getByText('All-time expenses').closest('div') as HTMLElement
    expect(within(allTime).getByText('57')).toBeInTheDocument()
  })

  it('shows zeros for an empty month', () => {
    render(<SummaryCards summary={makeSummary({ total_recorded_count: 12 })} />)
    expect(screen.getByText('₹0.00')).toBeInTheDocument()
    const month = screen.getByText('Expenses this month').closest('div') as HTMLElement
    expect(within(month).getByText('0')).toBeInTheDocument()
  })

  it('formats thousands with separators', () => {
    render(<SummaryCards summary={makeSummary({ total_spent: '10000.00' })} />)
    expect(screen.getByText('₹10,000.00')).toBeInTheDocument()
  })
})
