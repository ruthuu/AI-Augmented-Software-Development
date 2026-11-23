import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request } from './client'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

async function caught(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise
  } catch (failure) {
    expect(failure).toBeInstanceOf(ApiError)
    return failure as ApiError
  }
  throw new Error('Expected the request to fail')
}

describe('request', () => {
  it('returns the parsed JSON body on success', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { today: '2026-11-12' }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(request<{ today: string }>('/api/config')).resolves.toEqual({
      today: '2026-11-12',
    })
    expect(fetchMock).toHaveBeenCalledWith('/api/config', expect.objectContaining({ method: 'GET' }))
  })

  it('sends a JSON body with the JSON content type', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { id: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    await request('/api/expenses', { method: 'POST', body: { amount: '250.50' } })
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ amount: '250.50' }))
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  })

  it('returns undefined for a 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(request('/api/expenses/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('maps field errors from a 422 body into ApiError.errors', async () => {
    const body = {
      code: 'validation_error',
      message: 'Please correct the highlighted fields.',
      errors: [{ field: 'amount', message: 'Amount must be greater than zero' }],
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(422, body)))
    const error = await caught(request('/api/expenses', { method: 'POST', body: {} }))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
    expect(error.errors).toEqual([{ field: 'amount', message: 'Amount must be greater than zero' }])
    expect(error.fieldMessage('amount')).toBe('Amount must be greater than zero')
    expect(error.fieldMessage('description')).toBeUndefined()
  })

  it('reports a 404 with the server message', async () => {
    const body = { code: 'not_found', message: 'This expense no longer exists', errors: [] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(404, body)))
    const error = await caught(request('/api/expenses/9', { method: 'DELETE' }))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(404)
    expect(error.message).toBe('This expense no longer exists')
  })

  it('shows a plain message when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const error = await caught(request('/api/config'))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(0)
    expect(error.message).toBe('Could not reach the server. Try again.')
    expect(error.errors).toEqual([])
  })

  it('uses a generic message when an error body is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>boom</html>', { status: 502 })))
    const error = await caught(request('/api/config'))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(502)
    expect(error.message).not.toContain('<html>')
  })
})

describe('architecture rule', () => {
  it('only the api folder calls fetch', () => {
    const files = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true })
    const offenders = Object.entries(files)
      .filter(([path]) => !path.startsWith('/src/api/') && !path.includes('.test.'))
      .filter(([, source]) => /\bfetch\s*\(/.test(source as string))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })
})
