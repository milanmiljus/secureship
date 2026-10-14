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
  const [isLoading, setIsLoading] = useState(false)
  const [isReset, setIsReset] = useState(false)
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
        setError(data.message)
        setIsReset(true)
      } else {
        setError(data.message)
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

        {isReset ? (
          <button
            onClick={onClose}
            className="w-full py-3 bg-gray-700 text-white rounded-xl font-semibold hover:bg-gray-800 transition-colors"
          >
            Close
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={code.length !== 6 || isLoading}
            className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Verifying...' : 'Verify'}
          </button>
        )}
      </div>
    </div>
  )
}
