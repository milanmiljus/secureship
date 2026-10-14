import MessageBubble from "./MessageBubble";
import type { Message } from "./ChatWindow";

interface Props {
  messages: Message[];
  isEscalated?: boolean;
}

export default function MessageList({ messages }: Props) {
  return (
    <>
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          role={msg.role}
          content={msg.content}
          avatar={msg.avatar}
          shipments={msg.shipments}
        />
      ))}
    </>
  );
}
