import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ApiError } from './api/client'
import { saveBudget } from './api/budgets'
import { getConfig } from './api/config'
import { createExpense, deleteExpense, listExpenses, updateExpense } from './api/expenses'
import { getSummary } from './api/summary'
import { config, makeExpense, makeSummary } from './test/fixtures'

vi.mock('./api/config', () => ({ getConfig: vi.fn() }))
vi.mock('./api/summary', () => ({ getSummary: vi.fn() }))
vi.mock('./api/budgets', () => ({ saveBudget: vi.fn() }))
vi.mock('./api/expenses', () => ({
  listExpenses: vi.fn(),
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
}))

const getConfigMock = vi.mocked(getConfig)
const getSummaryMock = vi.mocked(getSummary)
const listMock = vi.mocked(listExpenses)
const createMock = vi.mocked(createExpense)
const updateMock = vi.mocked(updateExpense)
const deleteMock = vi.mocked(deleteExpense)
const saveBudgetMock = vi.mocked(saveBudget)

beforeEach(() => {
  for (const mock of [getConfigMock, getSummaryMock, listMock, createMock, updateMock, deleteMock, saveBudgetMock]) {
    mock.mockReset()
  }
  getSummaryMock.mockResolvedValue(makeSummary())
  listMock.mockResolvedValue([])
})

describe('App shell', () => {
  it('shows a loading indicator while the configuration loads', () => {
    getConfigMock.mockReturnValue(new Promise(() => {}))
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading')
  })

  it('shows the shell with the backend date once the configuration has loaded', async () => {
    getConfigMock.mockResolvedValue(config)
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'SpendWise' })).toBeInTheDocument()
    expect(screen.getByText('Today: 12 Nov 2026')).toBeInTheDocument()
    expect(await screen.findByText(/add your first expense/i)).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows an error with a retry when the configuration cannot be loaded', async () => {
    getConfigMock.mockRejectedValueOnce(new ApiError(0, 'Could not reach the server. Try again.'))
    getConfigMock.mockResolvedValueOnce(config)
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server. Try again.')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Today: 12 Nov 2026')).toBeInTheDocument()
    expect(getConfigMock).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('opens the dashboard on the month of the backend date', async () => {
    getConfigMock.mockResolvedValue(config)
    render(<App />)
    await screen.findByText(/add your first expense/i)
    expect(screen.getByLabelText('Month')).toHaveValue('2026-11')
    expect(getSummaryMock).toHaveBeenCalledWith('2026-11')
  })
})

describe('refresh after a change (SC-004)', () => {
  beforeEach(() => {
    getConfigMock.mockResolvedValue(config)
    listMock.mockResolvedValue([makeExpense()])
  })

  async function ready() {
    render(<App />)
    await screen.findByText('Lunch')
    await vi.waitFor(() => expect(getSummaryMock).toHaveBeenCalledTimes(1))
  }

  it('fetches the list and the summary again after an expense is added', async () => {
    createMock.mockResolvedValue(makeExpense({ id: 2 }))
    await ready()
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }))
    const dialog = screen.getByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Amount'), '10.00')
    await userEvent.type(within(dialog).getByLabelText('Description'), 'Tea')
    await userEvent.selectOptions(within(dialog).getByLabelText('Category'), 'Food')
    await userEvent.selectOptions(within(dialog).getByLabelText('Payment method'), 'Cash')
    await userEvent.type(within(dialog).getByLabelText('Date'), '2026-11-10')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    await vi.waitFor(() => expect(listMock).toHaveBeenCalledTimes(2))
    await vi.waitFor(() => expect(getSummaryMock).toHaveBeenCalledTimes(2))
  })

  it('fetches both again after an expense is edited', async () => {
    updateMock.mockResolvedValue(makeExpense({ amount: '300.00' }))
    await ready()
    await userEvent.click(screen.getByRole('button', { name: 'Edit Lunch' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' }))
    await vi.waitFor(() => expect(listMock).toHaveBeenCalledTimes(2))
    await vi.waitFor(() => expect(getSummaryMock).toHaveBeenCalledTimes(2))
  })

  it('fetches both again after an expense is deleted', async () => {
    deleteMock.mockResolvedValue(undefined)
    await ready()
    await userEvent.click(screen.getByRole('button', { name: 'Delete Lunch' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }))
    await vi.waitFor(() => expect(listMock).toHaveBeenCalledTimes(2))
    await vi.waitFor(() => expect(getSummaryMock).toHaveBeenCalledTimes(2))
  })

  it('fetches both again after a budget is saved', async () => {
    saveBudgetMock.mockResolvedValue({ month: '2026-11', amount: '1000.00' })
    await ready()
    await userEvent.type(screen.getByLabelText('Budget'), '1000')
    await userEvent.click(screen.getByRole('button', { name: 'Save budget' }))
    expect(saveBudgetMock).toHaveBeenCalledWith('2026-11', '1000')
    await vi.waitFor(() => expect(listMock).toHaveBeenCalledTimes(2))
    await vi.waitFor(() => expect(getSummaryMock).toHaveBeenCalledTimes(2))
  })

  it('shows the figures from the new summary after the refetch', async () => {
    getSummaryMock.mockResolvedValueOnce(makeSummary({ total_spent: '100.00', total_recorded_count: 1 }))
    getSummaryMock.mockResolvedValueOnce(makeSummary({ total_spent: '60.00', total_recorded_count: 1 }))
    deleteMock.mockResolvedValue(undefined)
    await ready()
    expect((await screen.findAllByText('₹100.00')).length).toBeGreaterThan(0)
    await userEvent.click(screen.getByRole('button', { name: 'Delete Lunch' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }))
    expect((await screen.findAllByText('₹60.00')).length).toBeGreaterThan(0)
    expect(screen.queryByText('₹100.00')).not.toBeInTheDocument()
  })

  it('changing the dashboard month fetches that month and leaves the list filters alone', async () => {
    await ready()
    const month = screen.getByLabelText('Month')
    fireEvent.change(month, { target: { value: '2026-10' } })
    await vi.waitFor(() => expect(getSummaryMock).toHaveBeenLastCalledWith('2026-10'))
    expect(screen.getByLabelText('Filter by month')).toHaveValue('')
  })
})
