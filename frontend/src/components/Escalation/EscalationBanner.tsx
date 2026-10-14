import { useState, useEffect } from 'react'

interface Props {
  script: string[]
  firstName?: string | null
}

export default function EscalationBanner({ script, firstName: _ }: Props) {
  const [visibleLines, setVisibleLines] = useState<string[]>([])

  useEffect(() => {
    // Reveal script lines with timed delays
    const delays = [0, 1500, 3000, 5000]
    const timers = script.map((line, i) =>
      setTimeout(() => {
        setVisibleLines(prev => [...prev, line])
      }, delays[i] ?? i * 1500)
    )
    return () => timers.forEach(clearTimeout)
  }, [script])

  return (
    <div className="mx-3 my-2 p-3 bg-blue-50 border border-blue-200 rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
        <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
          Human Support
        </span>
      </div>
      <div className="space-y-1">
        {visibleLines.map((line, i) => (
          <p key={i} className="text-sm text-gray-700">{line}</p>
        ))}
      </div>
    </div>
  )
}
