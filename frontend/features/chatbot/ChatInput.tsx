// features/chatbot/ChatInput.tsx
"use client";

import { useState } from "react";
import { useChatbotStore } from "@/stores/chatbot.store";

export function ChatInput() {
  const [text, setText] = useState("");
  const sendMessage = useChatbotStore((s) => s.sendMessage);
  const isLoading = useChatbotStore((s) => s.isLoading);

  const send = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    // ✅ 1) 스토어 액션 호출 (비동기)
    sendMessage(trimmed);
    setText("");
  };

  return (
    <div className="flex items-center gap-2">
      <input
        className="flex-1 rounded-xl border px-4 py-3 text-sm outline-none"
        placeholder={isLoading ? "답변을 기다리는 중..." : "궁금한 복지 정책을 입력해보세요..."}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.nativeEvent.isComposing) send();
        }}
      />
      <button
        type="button"
        onClick={send}
        className="rounded-xl bg-blue-800 px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400"
        disabled={isLoading}
      >
        전송
      </button>
    </div>
  );
}
