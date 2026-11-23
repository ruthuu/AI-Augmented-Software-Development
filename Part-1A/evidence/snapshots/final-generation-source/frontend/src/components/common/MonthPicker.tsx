import { FormField } from './FormField'

interface MonthPickerProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
}

// A native month input: the value is always "YYYY-MM" or an empty string.
export function MonthPicker({ id, label, value, onChange }: MonthPickerProps) {
  return (
    <FormField
      id={id}
      label={label}
      type="month"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}
