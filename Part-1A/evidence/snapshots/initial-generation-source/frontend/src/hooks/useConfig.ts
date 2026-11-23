import { useCallback, useEffect, useState } from 'react'
import { getConfig } from '../api/config'
import { errorMessage } from '../api/client'
import type { ConfigResponse } from '../api/types'

export function useConfig() {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    getConfig()
      .then((loaded) => {
        if (!cancelled) setConfig(loaded)
      })
      .catch((failure: unknown) => {
        if (!cancelled) setError(errorMessage(failure))
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  const retry = useCallback(() => {
    setError(null)
    setAttempt((count) => count + 1)
  }, [])
  return { config, error, loading: config === null && error === null, retry }
}
