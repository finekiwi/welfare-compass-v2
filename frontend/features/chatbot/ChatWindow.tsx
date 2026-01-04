// features/chatbot/ChatWindow.tsx
"use client";

import { useChatbotStore } from "@/stores/chatbot.store";
import { ChatMessageBubble } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

export function ChatWindow() {
  const messages = useChatbotStore((s) => s.messages);

  // ✅ ③ 이미지 구조를 단순화한 2컬럼: (왼쪽 요약) + (오른쪽 대화)
  return (
    <div className="grid grid-cols-1 gap-4 p-5 md:grid-cols-[320px_1fr]">
      {/* 왼쪽: 사용자 정보 요약(지금은 틀만) */}
      <aside className="rounded-xl border bg-gray-50 p-4">
        <div className="text-sm font-semibold">내 정보 요약</div>
        <div className="mt-3 space-y-2 text-xs text-gray-700">
          <Row label="나이" value="-" />
          <Row label="거주지" value="-" />
          <Row label="구직/재직" value="-" />
          <Row label="소득" value="-" />
        </div>

        <button className="mt-4 w-full rounded-xl border bg-white px-3 py-2 text-xs">
          내정보 업데이트
        </button>
      </aside>

      {/* 오른쪽: 채팅 */}
      <section className="flex min-h-[520px] flex-col rounded-xl border">
        <div className="flex-1 space-y-3 overflow-auto p-4">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
          ))}
        </div>

        <div className="border-t p-3">
          <ChatInput />
        </div>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-white px-3 py-2">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
