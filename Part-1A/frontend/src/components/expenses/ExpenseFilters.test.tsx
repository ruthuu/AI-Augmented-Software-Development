import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { config, makeExpense } from '../../test/fixtures'
import { ExpenseFilters } from './ExpenseFilters'
import { ExpensesSection } from './ExpensesSection'

function Harness() {
  const [version, setVersion] = useState(0)
  return <ExpensesSection config={config} version={version} onChanged={() => setVersion((v) => v + 1)} />
}

const fetchMock = vi.fn()

function respondWith(...lists: unknown[][]) {
  for (const list of lists) {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(list), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
  }
}

function requestedUrls(): string[] {
  return fetchMock.mock.calls.map((call) => String(call[0]))
}

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ExpenseFilters', () => {
  it('reports a chosen month', () => {
    const onChange = vi.fn()
    render(<ExpenseFilters config={config} filters={{ month: '', category: '' }} onChange={onChange} />)
    fireEvent.change(screen.getByLabelText('Filter by month'), { target: { value: '2026-11' } })
    expect(onChange).toHaveBeenCalledWith({ month: '2026-11', category: '' })
  })

  it('reports a chosen category and offers All', async () => {
    const onChange = vi.fn()
    render(<ExpenseFilters config={config} filters={{ month: '2026-11', category: '' }} onChange={onChange} />)
    const select = screen.getByLabelText('Filter by category')
    expect(screen.getByRole('option', { name: 'All' })).toHaveValue('')
    await userEvent.selectOptions(select, 'Food')
    expect(onChange).toHaveBeenCalledWith({ month: '2026-11', category: 'Food' })
  })

  it('offers a clear action only while a filter is applied', async () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <ExpenseFilters config={config} filters={{ month: '', category: '' }} onChange={onChange} />,
    )
    expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument()
    rerender(<ExpenseFilters config={config} filters={{ month: '2026-11', category: 'Food' }} onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(onChange).toHaveBeenCalledWith({ month: '', category: '' })
  })
})

describe('ExpensesSection filtering', () => {
  it('fetches the list with no query at first', async () => {
    respondWith([makeExpense()])
    render(<Harness />)
    await screen.findByText('Lunch')
    expect(requestedUrls()).toEqual(['/api/expenses'])
  })

  it('refetches with the month when one month is selected (1 interaction)', async () => {
    respondWith([makeExpense()], [])
    render(<Harness />)
    await screen.findByText('Lunch')
    fireEvent.change(screen.getByLabelText('Filter by month'), { target: { value: '2026-11' } })
    await screen.findByText('No expenses match these filters')
    expect(requestedUrls()).toEqual(['/api/expenses', '/api/expenses?month=2026-11'])
  })

  it('refetches with the category when one category is selected (1 interaction)', async () => {
    respondWith([makeExpense()], [makeExpense()])
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'Food')
    await screen.findByText('Lunch')
    expect(requestedUrls()).toEqual(['/api/expenses', '/api/expenses?category=Food'])
  })

  it('combines month and category', async () => {
    respondWith([], [], [])
    render(<Harness />)
    await screen.findByText(/add your first expense/i)
    fireEvent.change(screen.getByLabelText('Filter by month'), { target: { value: '2026-11' } })
    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'Food')
    await screen.findByText('No expenses match these filters')
    expect(requestedUrls().at(-1)).toBe('/api/expenses?month=2026-11&category=Food')
  })

  it('shows the no-match message with a clear action that lists everything again', async () => {
    respondWith([makeExpense()], [], [makeExpense()])
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'Bills')
    expect(await screen.findByText('No expenses match these filters')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(await screen.findByText('Lunch')).toBeInTheDocument()
    expect(requestedUrls().at(-1)).toBe('/api/expenses')
  })

  it('selecting All and clearing the month lists everything again', async () => {
    respondWith([makeExpense()], [], [makeExpense()], [makeExpense()])
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'Bills')
    await screen.findByText('No expenses match these filters')
    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'All')
    await screen.findByText('Lunch')
    expect(requestedUrls().at(-1)).toBe('/api/expenses')
  })

  it('does not say "no expenses yet" when filters are applied and nothing matches', async () => {
    respondWith([makeExpense()], [])
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'Bills')
    await screen.findByText('No expenses match these filters')
    expect(screen.queryByText(/add your first expense/i)).not.toBeInTheDocument()
  })
})
