import { formatMoney } from '../../utils/formatMoney'

interface OverBudgetAlertProps {
  overBy: string | null
}

export function OverBudgetAlert({ overBy }: OverBudgetAlertProps) {
  if (overBy === null) {
    return null
  }
  return (
    <div role="alert" className="over-budget">
      Budget exceeded by {formatMoney(overBy)}
    </div>
  )
}
