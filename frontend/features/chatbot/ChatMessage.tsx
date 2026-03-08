// features/chatbot/ChatMessage.tsx
"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-700 underline"
                >
                  {children}
                </a>
              ),
              p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-4 mb-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-4 mb-1">{children}</ol>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
