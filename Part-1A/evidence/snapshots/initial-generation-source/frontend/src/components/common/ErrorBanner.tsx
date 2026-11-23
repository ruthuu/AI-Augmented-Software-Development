import { Button } from './Button'

interface ErrorBannerProps {
  message: string
  onRetry?: () => void
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div role="alert" className="banner banner-error">
      <span>{message}</span>
      {onRetry ? <Button onClick={onRetry}>Retry</Button> : null}
    </div>
  )
}
