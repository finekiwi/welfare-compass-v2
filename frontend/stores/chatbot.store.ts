// stores/chatbot.store.ts
import { create } from "zustand";
import type { ChatMessage } from "@/features/chatbot/chatbot.types";

interface ChatbotState {
  isOpen: boolean;
  messages: ChatMessage[];
  open: () => void;
  close: () => void;
  reset: () => void;
  addMessage: (msg: ChatMessage) => void;
}

export const useChatbotStore = create<ChatbotState>((set) => ({
  isOpen: false,
  messages: [
    {
      id: "welcome",
      role: "assistant",
      content:
        "안녕하세요! 복지 혜택 찾기를 도와드릴게요. 현재 상황(거주지, 나이, 취업 상태 등)을 말해주시면 추천이 더 정확해져요.",
      createdAt: Date.now(),
    },
  ],
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  reset: () =>
    set({
      messages: [
        {
          id: "welcome",
          role: "assistant",
          content:
            "안녕하세요! 복지 혜택 찾기를 도와드릴게요. 현재 상황(거주지, 나이, 취업 상태 등)을 말해주시면 추천이 더 정확해져요.",
          createdAt: Date.now(),
        },
      ],
    }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
}));
