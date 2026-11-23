export type Intent = 'CREATE' | 'RESCHEDULE' | 'CLARIFY'

export interface AgentResult {
  intent: Intent
  title: string | null
  reminder_reference: string | null
  scheduled_at: string | null
  clarification: string | null
}

export interface InterpretResponse {
  result: AgentResult
  persisted: boolean
  note: string
}

export interface ApiErrorBody {
  error: { code: string; message: string }
}
