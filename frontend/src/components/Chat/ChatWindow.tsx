import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import MessageList from './MessageList'
import Composer from './Composer'
import CodeModal from '../Verification/CodeModal'
import EscalationBanner from '../Escalation/EscalationBanner'
import type { SessionState } from '../../types/chat'
import { createSessionSessionsPost, sendMessageChatPost } from '../../api/secureship'

interface Message {
  role: 'user' | 'assistant'
  content: string
  id: string
}

const SESSION_KEY = 'secureship_session_id'

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionState, setSessionState] = useState<SessionState>('anonymous')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState(false)
  const [showCodeModal, setShowCodeModal] = useState(false)
  const [isEscalated, setIsEscalated] = useState(false)
  const [escalationScript, setEscalationScript] = useState<string[] | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const existingId = localStorage.getItem(SESSION_KEY)
    if (existingId) {
      setSessionId(existingId)
    } else {
      createSession()
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, isEscalated])

  async function createSession() {
    try {
      const data = await createSessionSessionsPost()
      localStorage.setItem(SESSION_KEY, data.session_id)
      setSessionId(data.session_id)
      setSessionState(data.state as SessionState)
    } catch {
      setSessionError(true)
    }
  }

  async function sendMessage(text: string) {
    if (!sessionId || !text.trim() || isLoading) return

    const userMsg: Message = { role: 'user', content: text.trim(), id: crypto.randomUUID() }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)

    try {
      let data
      try {
        data = await sendMessageChatPost({ session_id: sessionId, message: text.trim() })
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          localStorage.removeItem(SESSION_KEY)
          await createSession()
          setError('Session expired. Please try sending your message again.')
          return
        }
        throw err
      }

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.message,
        id: crypto.randomUUID(),
      }
      setMessages(prev => [...prev, assistantMsg])
      setSessionState(data.state as SessionState)

      if (data.show_code_modal) {
        setShowCodeModal(true)
      }

      if (data.is_escalated && data.escalation_script) {
        setIsEscalated(true)
        setEscalationScript(data.escalation_script)
      }
    } catch {
      setError('Failed to send message. Please check your connection and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  function handleVerified() {
    setShowCodeModal(false)
    setSessionState('verified')
    const systemMsg: Message = {
      role: 'assistant',
      content: "You're verified! You can now ask about your shipments.",
      id: crypto.randomUUID(),
    }
    setMessages(prev => [...prev, systemMsg])
  }

  if (sessionError) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
        <p className="text-red-600 font-medium">Unable to connect to the support service.</p>
        <button
          onClick={() => { setSessionError(false); createSession() }}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }

  const isVerified = sessionState === 'verified'

  return (
    <>
      {showCodeModal && sessionId && (
        <CodeModal
          sessionId={sessionId}
          onVerified={handleVerified}
          onClose={() => setShowCodeModal(false)}
        />
      )}

      <div className={`bg-white rounded-2xl shadow-lg flex flex-col h-[600px] transition-colors duration-500 ${isEscalated ? 'border-2 border-blue-400' : ''}`}>
        {/* Chat header */}
        <div className={`px-6 py-4 border-b border-gray-100 flex items-center justify-between ${isEscalated ? 'bg-blue-50' : ''}`}>
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isEscalated ? 'bg-blue-500' : 'bg-green-500'}`} />
            <span className="font-semibold text-gray-800">
              {isEscalated ? 'Human Support' : 'SecureShip Assistant'}
            </span>
          </div>
          {isVerified && (
            <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
              ✓ Verified
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 && !isLoading && (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              Ask me about your shipment to get started.
            </div>
          )}
          <MessageList messages={messages} />

          {isEscalated && escalationScript && (
            <EscalationBanner script={escalationScript} />
          )}

          {isLoading && (
            <div className="flex gap-1 p-3 w-fit">
              <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          )}

          {error && (
            <div className="mt-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-gray-100 p-4">
          <Composer onSend={sendMessage} disabled={isLoading || !sessionId} />
        </div>
      </div>
    </>
  )
}
