import { request } from './client'
import type { Expense, ExpenseFilters, ExpenseInput } from './types'

export function listExpenses(filters: ExpenseFilters = { month: '', category: '' }): Promise<Expense[]> {
  const params = new URLSearchParams()
  if (filters.month) params.set('month', filters.month)
  if (filters.category) params.set('category', filters.category)
  const query = params.toString()
  return request<Expense[]>(query ? `/api/expenses?${query}` : '/api/expenses')
}

export function createExpense(input: ExpenseInput): Promise<Expense> {
  return request<Expense>('/api/expenses', { method: 'POST', body: input })
}

export function updateExpense(id: number, input: ExpenseInput): Promise<Expense> {
  return request<Expense>(`/api/expenses/${id}`, { method: 'PUT', body: input })
}

export function deleteExpense(id: number): Promise<void> {
  return request<void>(`/api/expenses/${id}`, { method: 'DELETE' })
}