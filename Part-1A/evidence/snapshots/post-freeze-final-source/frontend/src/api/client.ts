import type { FieldError } from './types'

export const NETWORK_ERROR_MESSAGE = 'Could not reach the server. Try again.'
const GENERIC_ERROR_MESSAGE = 'Something went wrong. Try again.'

export class ApiError extends Error {
  status: number
  errors: FieldError[]
  code: string

  constructor(status: number, message: string, errors: FieldError[] = [], code = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
    this.code = code
  }

  fieldMessage(field: string): string | undefined {
    return this.errors.find((error) => error.field === field)?.message
  }
}

export function errorMessage(failure: unknown): string {
  return failure instanceof Error && failure.message ? failure.message : GENERIC_ERROR_MESSAGE
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
}

interface ErrorBody {
  code?: string
  message?: string
  errors?: FieldError[]
}

async function readErrorBody(response: Response): Promise<ErrorBody> {
  try {
    return (await response.json()) as ErrorBody
  } catch {
    return {}
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const init: RequestInit = { method }
  if (options.body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(options.body)
  }
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError(0, NETWORK_ERROR_MESSAGE)
  }
  if (!response.ok) {
    const body = await readErrorBody(response)
    throw new ApiError(
      response.status,
      body.message ?? GENERIC_ERROR_MESSAGE,
      Array.isArray(body.errors) ? body.errors : [],
      body.code ?? '',
    )
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
