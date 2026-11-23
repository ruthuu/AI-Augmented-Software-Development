import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OverBudgetAlert } from './OverBudgetAlert'

describe('OverBudgetAlert', () => {
  it('is an alert stating the amount by which the budget is exceeded', () => {
    render(<OverBudgetAlert overBy="0.01" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Budget exceeded by ₹0.01')
  })

  it('formats larger amounts with separators', () => {
    render(<OverBudgetAlert overBy="1000.00" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Budget exceeded by ₹1,000.00')
  })

  it('renders nothing when the budget is not exceeded', () => {
    const { container } = render(<OverBudgetAlert overBy={null} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(container).toBeEmptyDOMElement()
  })
})
