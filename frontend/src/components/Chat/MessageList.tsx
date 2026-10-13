import MessageBubble from './MessageBubble'

interface Message {
  role: 'user' | 'assistant'
  content: string
  id: string
}

interface Props {
  messages: Message[]
}

export default function MessageList({ messages }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {messages.map(msg => (
        <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
      ))}
    </div>
  )
}
