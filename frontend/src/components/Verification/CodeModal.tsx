import { useState, useRef, useEffect } from 'react'
import { verifyCodeEndpointVerifyCodePost } from '../../api/secureship'

interface Props {
  sessionId: string
  onVerified: () => void
  onClose: () => void
}

export default function CodeModal({ sessionId, onVerified, onClose }: Props) {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  async function handleSubmit() {
    if (code.length !== 6 || isLoading) return
    setIsLoading(true)
    setError(null)

    try {
      const data = await verifyCodeEndpointVerifyCodePost({ session_id: sessionId, code })

      if (data.verified) {
        onVerified()
      } else if (data.reset) {
        // Max attempts or expired — close modal, show message in chat
        setError(data.message)
        setTimeout(onClose, 2000)
      } else {
        setError(data.message)
        setAttemptsRemaining(data.attempts_remaining ?? null)
        setCode('')
        inputRef.current?.focus()
      }
    } catch {
      setError('Failed to verify. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Verify your identity</h2>
        <p className="text-sm text-gray-500 mb-6">
          Enter the 6-digit code sent to your phone number.
        </p>

        <input
          ref={inputRef}
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
          onKeyDown={handleKeyDown}
          placeholder="000000"
          className="w-full text-center text-3xl tracking-widest font-mono border-2 border-gray-200 rounded-xl py-4 focus:outline-none focus:border-blue-500 mb-4"
          disabled={isLoading}
        />

        {error && (
          <p className="text-red-600 text-sm text-center mb-3">{error}</p>
        )}
        {attemptsRemaining !== null && attemptsRemaining > 0 && (
          <p className="text-amber-600 text-xs text-center mb-3">
            {attemptsRemaining} attempt{attemptsRemaining !== 1 ? 's' : ''} remaining
          </p>
        )}

        <button
          onClick={handleSubmit}
          disabled={code.length !== 6 || isLoading}
          className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'Verifying...' : 'Verify'}
        </button>
      </div>
    </div>
  )
}
