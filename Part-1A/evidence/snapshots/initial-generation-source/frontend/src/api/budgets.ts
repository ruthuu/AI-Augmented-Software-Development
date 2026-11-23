import { request } from './client'
import type { Budget } from './types'

export function saveBudget(month: string, amount: string): Promise<Budget> {
  return request<Budget>(`/api/budgets/${month}`, { method: 'PUT', body: { amount } })
}
