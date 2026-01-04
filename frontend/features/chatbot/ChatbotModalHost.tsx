// features/chatbot/ChatbotModalHost.tsx
"use client";

import { useChatbotStore } from "@/stores/chatbot.store";
import { ChatbotModal } from "./ChatbotModal";

export function ChatbotModalHost() {
  // ✅ layout에 붙어 있는 "전역 모달 호스트"
  // 상태가 열리면 오버레이를 띄웁니다.
  const isOpen = useChatbotStore((s) => s.isOpen);
  if (!isOpen) return null;
  return <ChatbotModal />;
}
