import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/client'
import { createExpense, updateExpense } from '../../api/expenses'
import { config, makeExpense } from '../../test/fixtures'
import { ExpenseForm } from './ExpenseForm'

vi.mock('../../api/expenses', () => ({
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  listExpenses: vi.fn(),
  deleteExpense: vi.fn(),
}))

const createMock = vi.mocked(createExpense)
const updateMock = vi.mocked(updateExpense)

function renderForm(expense: ReturnType<typeof makeExpense> | null = null) {
  const onSaved = vi.fn()
  const onCancel = vi.fn()
  const onStale = vi.fn()
  render(<ExpenseForm config={config} expense={expense} onSaved={onSaved} onCancel={onCancel} onStale={onStale} />)
  return { onSaved, onCancel, onStale }
}

async function fillValid() {
  await userEvent.type(screen.getByLabelText('Amount'), '250.50')
  await userEvent.type(screen.getByLabelText('Description'), 'Lunch')
  await userEvent.selectOptions(screen.getByLabelText('Category'), 'Food')
  await userEvent.selectOptions(screen.getByLabelText('Payment method'), 'UPI')
  await userEvent.type(screen.getByLabelText('Date'), '2026-11-10')
}

beforeEach(() => {
  createMock.mockReset()
  updateMock.mockReset()
})

describe('ExpenseForm', () => {
  it('offers exactly the configured categories and payment methods', () => {
    renderForm()
    const options = (label: string) =>
      within(screen.getByLabelText(label))
        .getAllByRole('option')
        .map((option) => (option as HTMLOptionElement).value)
        .filter((value) => value !== '')
    expect(options('Category')).toEqual(config.categories)
    expect(options('Payment method')).toEqual(config.payment_methods)
  })

  it('limits the date input to the backend date', () => {
    renderForm()
    expect(screen.getByLabelText('Date')).toHaveAttribute('max', '2026-11-12')
    expect(screen.getByLabelText('Date')).toHaveAttribute('min', '2000-01-01')
  })

  it('shows backend messages beside the matching fields and keeps the entered values', async () => {
    createMock.mockRejectedValue(
      new ApiError(422, 'Please correct the highlighted fields.', [
        { field: 'amount', message: 'Amount must be greater than zero' },
        { field: 'description', message: 'Description is required' },
        { field: 'category', message: 'Select a valid category' },
        { field: 'payment_method', message: 'Payment method is required' },
        { field: 'expense_date', message: 'Date cannot be in the future' },
      ]),
    )
    renderForm()
    await userEvent.type(screen.getByLabelText('Amount'), '0')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Amount must be greater than zero')).toBeInTheDocument()
    expect(screen.getByLabelText('Amount')).toHaveAccessibleDescription('Amount must be greater than zero')
    expect(screen.getByLabelText('Description')).toHaveAccessibleDescription('Description is required')
    expect(screen.getByLabelText('Category')).toHaveAccessibleDescription('Select a valid category')
    expect(screen.getByLabelText('Payment method')).toHaveAccessibleDescription('Payment method is required')
    expect(screen.getByLabelText('Date')).toHaveAccessibleDescription('Date cannot be in the future')
    expect(screen.getByLabelText('Amount')).toHaveValue('0')
  })

  it('submits the typed text without converting it', async () => {
    createMock.mockResolvedValue(makeExpense())
    const { onSaved } = renderForm()
    await fillValid()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(createMock).toHaveBeenCalledWith({
      amount: '250.50',
      description: 'Lunch',
      category: 'Food',
      payment_method: 'UPI',
      expense_date: '2026-11-10',
    })
    expect(onSaved).toHaveBeenCalledTimes(1)
  })

  it('calls the API once when Save is clicked twice quickly', async () => {
    createMock.mockReturnValue(new Promise(() => {}))
    renderForm()
    await fillValid()
    await userEvent.dblClick(screen.getByRole('button', { name: 'Save' }))
    expect(createMock).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  it('keeps the entered values and shows an error when saving fails', async () => {
    createMock.mockRejectedValue(new ApiError(0, 'Could not reach the server. Try again.'))
    const { onSaved } = renderForm()
    await fillValid()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server. Try again.')
    expect(screen.getByLabelText('Amount')).toHaveValue('250.50')
    expect(screen.getByLabelText('Description')).toHaveValue('Lunch')
    expect(screen.getByLabelText('Category')).toHaveValue('Food')
    expect(onSaved).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
  })

  it('submits with Enter', async () => {
    createMock.mockResolvedValue(makeExpense())
    renderForm()
    await fillValid()
    await userEvent.type(screen.getByLabelText('Description'), '{Enter}')
    expect(createMock).toHaveBeenCalledTimes(1)
  })

  it('closes on Cancel and on Escape without saving', async () => {
    const { onCancel } = renderForm()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await userEvent.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalled()
    expect(createMock).not.toHaveBeenCalled()
  })

  it('edits an existing expense with its current values', async () => {
    updateMock.mockResolvedValue(makeExpense({ amount: '300.00' }))
    const { onSaved } = renderForm(makeExpense({ id: 7 }))
    expect(screen.getByRole('dialog', { name: 'Edit expense' })).toBeInTheDocument()
    expect(screen.getByLabelText('Amount')).toHaveValue('250.50')
    expect(screen.getByLabelText('Date')).toHaveValue('2026-11-10')
    await userEvent.clear(screen.getByLabelText('Amount'))
    await userEvent.type(screen.getByLabelText('Amount'), '300.00')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(updateMock).toHaveBeenCalledWith(7, expect.objectContaining({ amount: '300.00' }))
    expect(createMock).not.toHaveBeenCalled()
    expect(onSaved).toHaveBeenCalledTimes(1)
  })

  it('tells the list to refresh when the edited expense no longer exists', async () => {
    updateMock.mockRejectedValue(new ApiError(404, 'This expense no longer exists', [], 'not_found'))
    const { onStale, onSaved } = renderForm(makeExpense({ id: 7 }))
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This expense no longer exists')
    expect(onStale).toHaveBeenCalledTimes(1)
    expect(onSaved).not.toHaveBeenCalled()
  })
})
