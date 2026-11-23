import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/client'
import { saveBudget } from '../../api/budgets'
import { makeSummary } from '../../test/fixtures'
import { BudgetPanel } from './BudgetPanel'

vi.mock('../../api/budgets', () => ({ saveBudget: vi.fn() }))

const saveMock = vi.mocked(saveBudget)

const withBudget = makeSummary({
  total_spent: '2500.75',
  expense_count: 2,
  budget: { month: '2026-11', amount: '10000.00' },
  remaining: '7499.25',
})

beforeEach(() => {
  saveMock.mockReset()
})

describe('BudgetPanel', () => {
  it('shows Spent and Remaining for a month with a budget and no warning', () => {
    render(<BudgetPanel month="2026-11" summary={withBudget} onSaved={vi.fn()} />)
    expect(screen.getByText('Spent')).toBeInTheDocument()
    expect(screen.getByText('₹2,500.75')).toBeInTheDocument()
    expect(screen.getByText('Remaining')).toBeInTheDocument()
    expect(screen.getByText('₹7,499.25')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Budget')).toHaveValue('10000.00')
  })

  it('shows Spent and a no-budget message when no budget is set', () => {
    render(<BudgetPanel month="2026-11" summary={makeSummary({ total_spent: '100.00' })} onSaved={vi.fn()} />)
    expect(screen.getByText('₹100.00')).toBeInTheDocument()
    expect(screen.getByText('No budget set for this month')).toBeInTheDocument()
    expect(screen.queryByText('Remaining')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the overage warning and Remaining 0.00 when over budget', () => {
    const over = makeSummary({
      total_spent: '10000.01',
      budget: { month: '2026-11', amount: '10000.00' },
      remaining: '0.00',
      over_budget: true,
      over_budget_by: '0.01',
    })
    render(<BudgetPanel month="2026-11" summary={over} onSaved={vi.fn()} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Budget exceeded by ₹0.01')
    expect(screen.getByText('₹0.00')).toBeInTheDocument()
  })

  it('saves the typed budget with one submission and refreshes', async () => {
    saveMock.mockResolvedValue({ month: '2026-11', amount: '12000.00' })
    const onSaved = vi.fn()
    render(<BudgetPanel month="2026-11" summary={makeSummary()} onSaved={onSaved} />)
    await userEvent.type(screen.getByLabelText('Budget'), '12000')
    await userEvent.click(screen.getByRole('button', { name: 'Save budget' })) // 1 interaction
    expect(saveMock).toHaveBeenCalledWith('2026-11', '12000')
    expect(onSaved).toHaveBeenCalledTimes(1)
  })

  it('submits with Enter', async () => {
    saveMock.mockResolvedValue({ month: '2026-11', amount: '5.00' })
    render(<BudgetPanel month="2026-11" summary={makeSummary()} onSaved={vi.fn()} />)
    await userEvent.type(screen.getByLabelText('Budget'), '5{Enter}')
    expect(saveMock).toHaveBeenCalledTimes(1)
  })

  it('shows the backend message beside the field and does not refresh', async () => {
    saveMock.mockRejectedValue(
      new ApiError(422, 'Please correct the highlighted fields.', [
        { field: 'amount', message: 'Budget can have at most 2 decimal places' },
      ]),
    )
    const onSaved = vi.fn()
    render(<BudgetPanel month="2026-11" summary={withBudget} onSaved={onSaved} />)
    await userEvent.clear(screen.getByLabelText('Budget'))
    await userEvent.type(screen.getByLabelText('Budget'), '12000.999')
    await userEvent.click(screen.getByRole('button', { name: 'Save budget' }))
    expect(await screen.findByText('Budget can have at most 2 decimal places')).toBeInTheDocument()
    expect(screen.getByLabelText('Budget')).toHaveAccessibleDescription('Budget can have at most 2 decimal places')
    expect(screen.getByLabelText('Budget')).toHaveValue('12000.999')
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('shows a network failure as an error and keeps the value', async () => {
    saveMock.mockRejectedValue(new ApiError(0, 'Could not reach the server. Try again.'))
    render(<BudgetPanel month="2026-11" summary={makeSummary()} onSaved={vi.fn()} />)
    await userEvent.type(screen.getByLabelText('Budget'), '100')
    await userEvent.click(screen.getByRole('button', { name: 'Save budget' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server. Try again.')
    expect(screen.getByLabelText('Budget')).toHaveValue('100')
  })

  it('ignores a second click while saving', async () => {
    saveMock.mockReturnValue(new Promise(() => {}))
    render(<BudgetPanel month="2026-11" summary={makeSummary()} onSaved={vi.fn()} />)
    await userEvent.type(screen.getByLabelText('Budget'), '100')
    await userEvent.dblClick(screen.getByRole('button', { name: 'Save budget' }))
    expect(saveMock).toHaveBeenCalledTimes(1)
  })
})
