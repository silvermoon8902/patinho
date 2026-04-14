import { useState, useRef, useEffect } from "react";
import type { ChatMessage } from "@/store/chatSlice";

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  connected: boolean;
  currentUserId?: string;
}

export default function ChatWindow({
  messages,
  onSendMessage,
  connected,
  currentUserId,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput("");
  };

  return (
    <div className="chat-window">
      <div className="chat-header-bar">
        <span className="chat-title">Chat</span>
        <span className={`chat-status ${connected ? "chat-online" : "chat-offline"}`}>
          {connected ? "Conectado" : "Desconectado"}
        </span>
      </div>

      <div className="chat-messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat-empty">Nenhuma mensagem ainda</div>
        )}
        {messages.map((msg) => {
          if (msg.is_system) {
            return (
              <div key={msg.id} className="chat-message-system">
                {msg.content}
              </div>
            );
          }
          const isOwn = msg.user_id === currentUserId;
          return (
            <div
              key={msg.id}
              className={`chat-message ${isOwn ? "chat-message-own" : ""}`}
            >
              {!isOwn && (
                <span className="chat-message-username">{msg.username}</span>
              )}
              <div className="chat-bubble">
                <span className="chat-bubble-text">{msg.content}</span>
                <span className="chat-bubble-time">
                  {formatTime(msg.created_at)}
                </span>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
          placeholder="Escreva uma mensagem..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!connected}
        />
        <button
          type="submit"
          className="btn btn-primary chat-send-btn"
          disabled={!connected || !input.trim()}
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
