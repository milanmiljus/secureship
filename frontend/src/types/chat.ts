export type SessionState =
  | 'anonymous'
  | 'collecting_identity'
  | 'code_sent'
  | 'awaiting_code'
  | 'verified'
  | 'escalated_to_human'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  id: string
}

export interface ChatResponse {
  message: string
  state: SessionState
  show_code_modal: boolean
  is_escalated: boolean
}

export interface CreateSessionResponse {
  session_id: string
  state: SessionState
}
