import { useState } from 'react'
import { ErrorBanner } from './components/common/ErrorBanner'
import { LoadingIndicator } from './components/common/LoadingIndicator'
import { DashboardSection } from './components/dashboard/DashboardSection'
import { ExpensesSection } from './components/expenses/ExpensesSection'
import { useConfig } from './hooks/useConfig'
import { formatDate } from './utils/formatDate'

export default function App() {
  const { config, error, loading, retry } = useConfig()
  const [version, setVersion] = useState(0)
  const refresh = () => setVersion((count) => count + 1)

  return (
    <main className="page">
      <header className="page-header">
        <h1>SpendWise</h1>
        {config ? <p className="today">Today: {formatDate(config.today)}</p> : null}
      </header>
      {loading ? <LoadingIndicator /> : null}
      {error ? <ErrorBanner message={error} onRetry={retry} /> : null}
      {config ? (
        <div className="layout">
          <DashboardSection config={config} version={version} onChanged={refresh} />
          <ExpensesSection config={config} version={version} onChanged={refresh} />
        </div>
      ) : null}
    </main>
  )
}