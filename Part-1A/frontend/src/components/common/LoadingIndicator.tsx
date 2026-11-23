interface LoadingIndicatorProps {
  label?: string
}

export function LoadingIndicator({ label = 'Loading' }: LoadingIndicatorProps) {
  return (
    <p role="status" className="loading">
      {label}…
    </p>
  )
}
