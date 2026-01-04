// features/chatbot/ChatbotModal.tsx
"use client";

import { useChatbotStore } from "@/stores/chatbot.store";
import { ChatWindow } from "./ChatWindow";

export function ChatbotModal() {
  const close = useChatbotStore((s) => s.close);

  // ✅ ③ 이미지처럼 화면 위에 "대화창"을 띄우는 오버레이
  return (
    <div className="fixed inset-0 z-50">
      {/* 배경 딤 */}
      <button
        aria-label="close"
        className="absolute inset-0 bg-black/40"
        onClick={close}
      />

      {/* 모달 본체 */}
      <div className="absolute left-1/2 top-1/2 w-[min(1100px,95vw)] -translate-x-1/2 -translate-y-1/2">
        <div className="rounded-2xl bg-white shadow-xl">
          <div className="flex items-center justify-between border-b px-5 py-3">
            <div className="text-sm font-semibold">복지 상담</div>
            <button
              onClick={close}
              className="rounded-lg border px-3 py-1 text-xs text-gray-700"
            >
              닫기
            </button>
          </div>

          <ChatWindow />
        </div>
      </div>
    </div>
  );
}
