export interface FieldError {
  field: string
  message: string
}

export interface ConfigResponse {
  today: string
  currency: string
  categories: string[]
  payment_methods: string[]
  limits: {
    max_expense: string
    max_budget: string
    max_description_length: number
    min_date: string
  }
}

export interface Expense {
  id: number
  amount: string
  description: string
  category: string
  payment_method: string
  expense_date: string
  created_at: string
  updated_at: string
}

export interface ExpenseInput {
  amount: string
  description: string
  category: string
  payment_method: string
  expense_date: string
}

export interface ExpenseFilters {
  month: string
  category: string
}

export interface Budget {
  month: string
  amount: string
}

export interface CategoryTotal {
  category: string
  total: string
  count: number
}

export interface Summary {
  month: string
  total_spent: string
  expense_count: number
  total_recorded_count: number
  by_category: CategoryTotal[]
  budget: Budget | null
  remaining: string | null
  over_budget: boolean
  over_budget_by: string | null
}
