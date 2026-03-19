// features/chatbot/ThinkingIndicator.tsx
import { useEffect, useState } from "react";
import Image from "next/image";

const THINKING_STEPS = [
  "질문의 의도를 파악하고 있어요",
  "가장 적합한 복지 정보를 찾는 중이에요",
  "관련 정책 데이터를 분석하고 있어요",
  "데이터를 꼼꼼하게 대조하고 있어요",
  "답변 내용을 정리하고 있어요",
  "조금만 더 기다려 주세요",
];

export function ThinkingIndicator() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % THINKING_STEPS.length);
    }, 6000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-start gap-3">
      <Image
        src="/mascot/chatbot.png"
        alt="챗봇 아이콘"
        width={50}
        height={50}
        className="h-11 w-11 shrink-0 p-1"
      />
      <div className="max-w-[78%] rounded-2xl bg-gray-100 px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="animate-pulse">{THINKING_STEPS[stepIndex]}...</span>
        </div>
      </div>
    </div>
  );
}

