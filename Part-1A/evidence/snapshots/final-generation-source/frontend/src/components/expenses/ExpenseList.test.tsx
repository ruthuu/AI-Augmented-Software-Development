import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/client'
import { createExpense, deleteExpense, listExpenses, updateExpense } from '../../api/expenses'
import { config, makeExpense } from '../../test/fixtures'
import { ExpenseList } from './ExpenseList'
import { ExpensesSection } from './ExpensesSection'

vi.mock('../../api/expenses', () => ({
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  listExpenses: vi.fn(),
  deleteExpense: vi.fn(),
}))

const listMock = vi.mocked(listExpenses)
const deleteMock = vi.mocked(deleteExpense)
const createMock = vi.mocked(createExpense)
const updateMock = vi.mocked(updateExpense)

function Harness() {
  const [version, setVersion] = useState(0)
  return <ExpensesSection config={config} version={version} onChanged={() => setVersion((v) => v + 1)} />
}

beforeEach(() => {
  listMock.mockReset()
  deleteMock.mockReset()
  createMock.mockReset()
  updateMock.mockReset()
})

describe('ExpenseList display', () => {
  it('shows amount, date, and fields in the display format', () => {
    render(<ExpenseList expenses={[makeExpense()]} onEdit={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('₹250.50')).toBeInTheDocument()
    expect(screen.getByText('10 Nov 2026')).toBeInTheDocument()
    expect(screen.getByText('Lunch')).toBeInTheDocument()
    expect(screen.getByText('Food')).toBeInTheDocument()
    expect(screen.getByText('UPI')).toBeInTheDocument()
  })

  it('renders markup in a description as plain text', () => {
    const text = '<b>Tom & "Jerry\'s"</b>'
    const { container } = render(
      <ExpenseList expenses={[makeExpense({ description: text })]} onEdit={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(screen.getByText(text)).toBeInTheDocument()
    expect(container.querySelector('b')).toBeNull()
  })

  it('keeps the order it is given', () => {
    render(
      <ExpenseList
        expenses={[makeExpense({ id: 2, description: 'second' }), makeExpense({ id: 1, description: 'first' })]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('second')
    expect(items[1]).toHaveTextContent('first')
  })
})

describe('ExpensesSection', () => {
  it('shows a loading indicator, then the list', async () => {
    listMock.mockResolvedValue([makeExpense()])
    render(<Harness />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading')
    expect(await screen.findByText('₹250.50')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows a prompt to add the first expense when the list is empty', async () => {
    listMock.mockResolvedValue([])
    render(<Harness />)
    expect(await screen.findByText(/add your first expense/i)).toBeInTheDocument()
  })

  it('shows an error with retry when the list cannot be loaded', async () => {
    listMock.mockRejectedValueOnce(new ApiError(0, 'Could not reach the server. Try again.'))
    listMock.mockResolvedValueOnce([makeExpense()])
    render(<Harness />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server. Try again.')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('₹250.50')).toBeInTheDocument()
  })

  it('deletes after confirmation: choose Delete (1), confirm (2)', async () => {
    listMock.mockResolvedValueOnce([makeExpense()]).mockResolvedValueOnce([])
    deleteMock.mockResolvedValue(undefined)
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.click(screen.getByRole('button', { name: 'Delete Lunch' })) // interaction 1
    const dialog = screen.getByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' })) // interaction 2
    expect(deleteMock).toHaveBeenCalledWith(1)
    await screen.findByText(/add your first expense/i)
    expect(screen.queryByText('Lunch')).not.toBeInTheDocument()
  })

  it('keeps the expense when the delete is cancelled', async () => {
    listMock.mockResolvedValue([makeExpense()])
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.click(screen.getByRole('button', { name: 'Delete Lunch' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }))
    expect(deleteMock).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByText('Lunch')).toBeInTheDocument()
  })

  it('shows the server message and refreshes when the expense no longer exists', async () => {
    listMock.mockResolvedValueOnce([makeExpense()]).mockResolvedValueOnce([])
    deleteMock.mockRejectedValue(new ApiError(404, 'This expense no longer exists', [], 'not_found'))
    render(<Harness />)
    await screen.findByText('Lunch')
    await userEvent.click(screen.getByRole('button', { name: 'Delete Lunch' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This expense no longer exists')
    await screen.findByText(/add your first expense/i)
    expect(listMock).toHaveBeenCalledTimes(2)
  })

  it('adds with two interactions: open the form (1), submit (2)', async () => {
    listMock.mockResolvedValueOnce([]).mockResolvedValueOnce([makeExpense()])
    createMock.mockResolvedValue(makeExpense())
    render(<Harness />)
    await screen.findByText(/add your first expense/i)
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' })) // interaction 1
    await userEvent.type(screen.getByLabelText('Amount'), '250.50')
    await userEvent.type(screen.getByLabelText('Description'), 'Lunch')
    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Food')
    await userEvent.selectOptions(screen.getByLabelText('Payment method'), 'UPI')
    await userEvent.type(screen.getByLabelText('Date'), '2026-11-10')
    await userEvent.click(screen.getByRole('button', { name: 'Save' })) // interaction 2
    expect(await screen.findByText('₹250.50')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(createMock).toHaveBeenCalledTimes(1)
  })

  it('edits with two interactions: open the form (1), submit (2)', async () => {
    listMock
      .mockResolvedValueOnce([makeExpense()])
      .mockResolvedValueOnce([makeExpense({ amount: '300.00' })])
    updateMock.mockResolvedValue(makeExpense({ amount: '300.00' }))
    render(<Harness />)
    await screen.findByText('₹250.50')
    await userEvent.click(screen.getByRole('button', { name: 'Edit Lunch' })) // interaction 1
    await userEvent.clear(screen.getByLabelText('Amount'))
    await userEvent.type(screen.getByLabelText('Amount'), '300.00')
    await userEvent.click(screen.getByRole('button', { name: 'Save' })) // interaction 2
    expect(await screen.findByText('₹300.00')).toBeInTheDocument()
    expect(updateMock).toHaveBeenCalledTimes(1)
    expect(createMock).not.toHaveBeenCalled()
  })
})