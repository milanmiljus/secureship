const STATUS_PATTERNS: Array<{ pattern: RegExp; label: string; color: string }> = [
  { pattern: /\b(out.?for.?delivery)\b/i, label: 'Out for Delivery', color: 'bg-amber-100 text-amber-800' },
  { pattern: /\b(in.?transit)\b/i, label: 'In Transit', color: 'bg-blue-100 text-blue-800' },
  { pattern: /\bdelivered\b/i, label: 'Delivered', color: 'bg-green-100 text-green-800' },
  { pattern: /\bexception\b/i, label: 'Exception', color: 'bg-red-100 text-red-800' },
  { pattern: /\b(label.?created)\b/i, label: 'Label Created', color: 'bg-gray-100 text-gray-700' },
]

function detectStatus(text: string) {
  for (const s of STATUS_PATTERNS) {
    if (s.pattern.test(text)) return s
  }
  return null
}

interface Props {
  role: 'user' | 'assistant'
  content: string
}

export default function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user'
  const statusMatch = !isUser ? detectStatus(content) : null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
        }`}
      >
        {content}
        {statusMatch && (
          <div className="mt-2">
            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusMatch.color}`}>
              {statusMatch.label}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
