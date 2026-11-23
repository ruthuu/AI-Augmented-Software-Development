import { request } from './client'
import type { ConfigResponse } from './types'

export function getConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>('/api/config')
}
