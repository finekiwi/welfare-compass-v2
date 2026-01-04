// features/chatbot/ChatInput.tsx
"use client";

import { useState } from "react";
import { useChatbotStore } from "@/stores/chatbot.store";

export function ChatInput() {
  const [text, setText] = useState("");
  const addMessage = useChatbotStore((s) => s.addMessage);

  const send = () => {
    const trimmed = text.trim();
    if (!trimmed) return;

    // ✅ 1) 사용자 메시지 추가
    addMessage({
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    });

    setText("");

    // ✅ 2) 지금은 백엔드 연결 전이므로 "임시 응답"을 추가
    // 나중에 SSE 붙일 때 이 부분만 교체하면 UI는 그대로 유지됩니다.
    setTimeout(() => {
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "좋아요. 거주지(구), 나이, 취업 상태, 소득 수준 중 아는 것부터 알려주시면 추천 정확도가 올라가요.",
        createdAt: Date.now(),
      });
    }, 400);
  };

  return (
    <div className="flex items-center gap-2">
      <input
        className="flex-1 rounded-xl border px-4 py-3 text-sm outline-none"
        placeholder="궁금한 복지 정책을 입력해보세요..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") send();
        }}
      />
      <button
        type="button"
        onClick={send}
        className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white"
      >
        전송
      </button>
    </div>
  );
}
