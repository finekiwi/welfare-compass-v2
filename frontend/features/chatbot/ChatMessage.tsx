// features/chatbot/ChatMessage.tsx
import type { ChatMessage } from "./chatbot.types";

export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser ? "bg-blue-800 text-white" : "bg-gray-100 text-gray-900",
        ].join(" ")}
      >
        {message.content}
      </div>
    </div>
  );
}
