import { useState, useEffect, useRef } from "react";
import axios from "axios";
import MessageList from "./MessageList";
import Composer from "./Composer";
import CodeModal from "../Verification/CodeModal";
import type { SessionState } from "../../types/chat";
import type { ShipmentOut } from "../../api/secureship";
import {
  createSessionSessionsPost,
  sendMessageChatPost,
} from "../../api/secureship";

export interface Message {
  role: "user" | "assistant";
  content: string;
  id: string;
  avatar?: "robot" | "human" | "banner";
  shipments?: ShipmentOut[];
}

const SESSION_KEY = "secureship_session_id";

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>("anonymous");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState(false);
  const [showCodeModal, setShowCodeModal] = useState(false);
  const [isEscalated, setIsEscalated] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const existingId = localStorage.getItem(SESSION_KEY);
    if (existingId) {
      setSessionId(existingId);
    } else {
      createSession();
    }
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function createSession() {
    try {
      const data = await createSessionSessionsPost();
      localStorage.setItem(SESSION_KEY, data.session_id);
      setSessionId(data.session_id);
      setSessionState(data.state as SessionState);
    } catch {
      setSessionError(true);
    }
  }

  async function sendMessage(text: string) {
    if (!sessionId || !text.trim() || isLoading) return;

    const userMsg: Message = {
      role: "user",
      content: text.trim(),
      id: crypto.randomUUID(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      let data;
      try {
        data = await sendMessageChatPost({
          session_id: sessionId,
          message: text.trim(),
        });
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          localStorage.removeItem(SESSION_KEY);
          await createSession();
          setError("Session expired. Please try sending your message again.");
          return;
        }
        throw err;
      }

      if (data.is_escalated && data.escalation_script && !isEscalated) {
        const script = data.escalation_script; // [line0, line1, line2, line3]
        setIsEscalated(true);

        // 1. Banner box (lines 1–2) appears first — inline in message stream
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: JSON.stringify([script[1], script[2]]),
            id: crypto.randomUUID(),
            avatar: "banner",
          },
        ]);

        // 2. Bot message (line 0) — robot announces the transfer
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: script[0],
              id: crypto.randomUUID(),
              avatar: "robot",
            },
          ]);
        }, 1500);

        // 3. Melany's greeting (line 3) — human message after delay
        setTimeout(() => {
          if (script[3]) {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: script[3],
                id: crypto.randomUUID(),
                avatar: "human",
              },
            ]);
          }
        }, 5000);
      } else {
        const assistantMsg: Message = {
          role: "assistant",
          content: data.message,
          id: crypto.randomUUID(),
          avatar: isEscalated ? "human" : "robot",
          shipments: data.shipments ?? undefined,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }

      setSessionState(data.state as SessionState);
      if (data.show_code_modal) setShowCodeModal(true);
    } catch {
      setError(
        "Failed to send message. Please check your connection and try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleVerified() {
    setShowCodeModal(false);
    setSessionState("verified");
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "You're verified! You can now ask about your shipments.",
        id: crypto.randomUUID(),
      },
    ]);
  }

  if (sessionError) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
        <p className="text-red-600 font-medium">
          Unable to connect to the support service.
        </p>
        <button
          onClick={() => {
            setSessionError(false);
            createSession();
          }}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const isVerified = sessionState === "verified";

  const BotIcon = () => (
    <svg
      className="w-5 h-5 text-gray-500"
      viewBox="0 0 24 24"
      fill="currentColor"
    >
      <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M9 11a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2m6 0a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2z" />
    </svg>
  );

  const HumanIcon = () => (
    <svg
      className="w-5 h-5 text-blue-500"
      viewBox="0 0 24 24"
      fill="currentColor"
    >
      <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" />
    </svg>
  );

  const thinkingAvatar = isEscalated ? (
    <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
      <HumanIcon />
    </div>
  ) : (
    <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
      <BotIcon />
    </div>
  );

  return (
    <>
      {showCodeModal && sessionId && (
        <CodeModal
          sessionId={sessionId}
          onVerified={handleVerified}
          onClose={() => setShowCodeModal(false)}
        />
      )}

      <div
        className={`bg-white rounded-2xl shadow-lg flex flex-col h-[600px] transition-colors duration-500 ${isEscalated ? "border-2 border-blue-400" : ""}`}
      >
        {/* Header */}
        <div
          className={`px-6 py-4 border-b border-gray-100 flex items-center justify-between ${isEscalated ? "bg-blue-50" : ""}`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${isEscalated ? "bg-blue-500" : "bg-green-500"}`}
            />
            <span className="font-semibold text-gray-800">
              {isEscalated ? "Human Support" : "SecureShip Assistant"}
            </span>
          </div>
          {isVerified && (
            <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
              ✓ Verified
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {messages.length === 0 && !isLoading && (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              Ask me about your shipment to get started.
            </div>
          )}

          <MessageList messages={messages} isEscalated={isEscalated} />

          {isLoading && (
            <div className="flex justify-start items-end gap-2">
              {thinkingAvatar}
              <div className="flex gap-1 bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3">
                <div
                  className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-gray-100 p-4">
          <Composer onSend={sendMessage} disabled={isLoading || !sessionId} />
        </div>
      </div>
    </>
  );
}
