import type { ConfigResponse, ExpenseFilters as Filters } from '../../api/types'
import { Button } from '../common/Button'
import { MonthPicker } from '../common/MonthPicker'
import { SelectField } from '../common/SelectField'

interface ExpenseFiltersProps {
  config: ConfigResponse
  filters: Filters
  onChange: (filters: Filters) => void
  showClear?: boolean
}

export function ExpenseFilters({ config, filters, onChange, showClear = true }: ExpenseFiltersProps) {
  const active = filters.month !== '' || filters.category !== ''
  return (
    <div className="filters">
      <MonthPicker
        id="filter-month"
        label="Filter by month"
        value={filters.month}
        onChange={(month) => onChange({ ...filters, month })}
      />
      <SelectField
        id="filter-category"
        label="Filter by category"
        placeholder="All"
        options={config.categories}
        value={filters.category}
        onChange={(event) => onChange({ ...filters, category: event.target.value })}
      />
      {active && showClear ? (
        <Button onClick={() => onChange({ month: '', category: '' })}>Clear filters</Button>
      ) : null}
    </div>
  )
}