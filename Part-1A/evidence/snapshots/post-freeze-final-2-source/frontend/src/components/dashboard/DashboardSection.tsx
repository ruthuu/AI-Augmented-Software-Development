import { useState } from 'react'
import type { ConfigResponse } from '../../api/types'
import { useSummary } from '../../hooks/useSummary'
import { monthOf } from '../../utils/month'
import { BudgetPanel } from '../budget/BudgetPanel'
import { ErrorBanner } from '../common/ErrorBanner'
import { LoadingIndicator } from '../common/LoadingIndicator'
import { MonthPicker } from '../common/MonthPicker'
import { CategoryBreakdown } from './CategoryBreakdown'
import { SummaryCards } from './SummaryCards'

interface DashboardSectionProps {
  config: ConfigResponse
  version: number
  onChanged: () => void
}

// The dashboard month is independent of the expense list's own filters (FR-032).
export function DashboardSection({ config, version, onChanged }: DashboardSectionProps) {
  const [month, setMonth] = useState(monthOf(config.today))
  const { summary, loading, error, reload } = useSummary(month, version)

  return (
    <section className="section" aria-labelledby="dashboard-heading">
      <h2 id="dashboard-heading">Dashboard</h2>
      <MonthPicker
        id="selected-month"
        label="Month"
        value={month}
        onChange={(value) => value && setMonth(value)}
      />
      {error ? <ErrorBanner message={error} onRetry={reload} /> : null}
      {loading && !summary ? <LoadingIndicator label="Loading summary" /> : null}
      {summary ? <SummaryCards summary={summary} /> : null}
      <BudgetPanel key={month} month={month} summary={summary} onSaved={onChanged} />
      {summary ? <CategoryBreakdown summary={summary} /> : null}
    </section>
  )
}