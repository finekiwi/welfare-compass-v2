// features/chatbot/ChatbotLauncher.tsx
"use client";

import { useChatbotStore } from "@/stores/chatbot.store";

export function ChatbotLauncher() {
  const open = useChatbotStore((s) => s.open);

  // ✅ ② 이미지처럼 메인에 배치되는 챗봇 런처 영역
  return (
    <section className="overflow-hidden rounded-2xl border bg-gradient-to-r from-slate-700 to-slate-600 p-6 text-white">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold">
            안녕하세요! 복지 혜택 찾기를 도와드리겠습니다.
          </p>
          <p className="mt-1 text-xs text-white/80">
            거주지, 나이, 취업 상태 등을 알려주시면 맞춤형 추천이 가능해요.
          </p>
        </div>

        <button
          type="button"
          onClick={open}
          className="mt-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-800 md:mt-0"
        >
          챗봇 열기
        </button>
      </div>

      <div className="mt-4">
        <input
          className="w-full rounded-xl px-4 py-3 text-sm text-slate-900 outline-none"
          placeholder="내용을 입력해보세요… (여긴 미리보기)"
          disabled
        />
      </div>
    </section>
  );
}
