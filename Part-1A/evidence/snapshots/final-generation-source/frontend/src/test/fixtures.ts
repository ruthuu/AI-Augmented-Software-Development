import type { ConfigResponse, Expense, Summary } from '../api/types'

export const config: ConfigResponse = {
  today: '2026-11-12',
  currency: 'INR',
  categories: ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Healthcare', 'Education', 'Other'],
  payment_methods: ['Cash', 'Credit Card', 'Debit Card', 'UPI', 'Net Banking', 'Other'],
  limits: {
    max_expense: '9999999.99',
    max_budget: '99999999.99',
    max_description_length: 200,
    min_date: '2000-01-01',
  },
}

export function makeExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 1,
    amount: '250.50',
    description: 'Lunch',
    category: 'Food',
    payment_method: 'UPI',
    expense_date: '2026-11-10',
    created_at: '2026-11-12T08:15:00Z',
    updated_at: '2026-11-12T08:15:00Z',
    ...overrides,
  }
}


export function makeSummary(overrides: Partial<Summary> = {}): Summary {
  return {
    month: '2026-11',
    total_spent: '0.00',
    expense_count: 0,
    total_recorded_count: 0,
    by_category: [],
    budget: null,
    remaining: null,
    over_budget: false,
    over_budget_by: null,
    ...overrides,
  }
}