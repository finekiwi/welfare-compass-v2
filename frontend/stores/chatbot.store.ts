// stores/chatbot.store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { ChatMessage } from "@/features/chatbot/chatbot.types";
import { chatbotApi } from "@/features/chatbot/chatbot.api";

interface ChatbotState {
  isOpen: boolean;
  isLoading: boolean;
  sessionId: string | null;
  messages: ChatMessage[];

  open: () => Promise<void>;
  close: () => void;
  reset: () => void;

  /** 사용자 메시지 전송 (비동기) */
  sendMessage: (content: string) => Promise<void>;
}

export const useChatbotStore = create<ChatbotState>()(
  devtools((set, get) => ({
    isOpen: false,
    isLoading: false,
    sessionId: null,
    messages: [],

    open: async () => {
      set({ isOpen: true });

      // 이미 세션이 있으면 재사용
      if (get().sessionId) return;

      try {
        set({ isLoading: true });
        // 세션 생성 API 호출
        const session = await chatbotApi.createSession();
        set({
          sessionId: session.id,
          messages: session.messages, // 웰컴 메시지 포함됨
        });
      } catch (error) {
        console.error("Failed to create chat session:", error);
        // 에러 처리 (필요시 UI 표시)
      } finally {
        set({ isLoading: false });
      }
    },

    close: () => set({ isOpen: false }),

    reset: () => {
      set({
        sessionId: null,
        messages: [],
        isLoading: false,
      });
      // 다시 열 때 새 세션 생성됨
    },

    sendMessage: async (content: string) => {
      const { sessionId, messages } = get();
      if (!sessionId) return;

      // 1. 사용자 메시지 낙관적 추가 (Optimistic UI)
      const tempUserMsg: ChatMessage = {
        id: crypto.randomUUID(), // 임시 ID
        role: "user",
        content,
        createdAt: Date.now(),
      };

      set({
        isLoading: true,
        messages: [...messages, tempUserMsg],
      });

      try {
        // 2. 메시지 전송 API 호출
        const response = await chatbotApi.sendMessage(sessionId, content);

        // 3. 응답으로 상태 업데이트 (실제 ID 등 동기화)
        set((state) => ({
          messages: [
            ...state.messages.slice(0, -1), // 임시 메시지 제거
            response.userMessage, // 실제 저장된 유저 메시지
            response.assistantMessage, // 어시스턴트 응답
          ],
        }));
      } catch (error) {
        console.error("Failed to send message:", error);
        // 에러 시 롤백 또는 에러 표시 로직 필요
        // 여기선 간단히 임시 메시지 유지하고 에러 상태만 해제
      } finally {
        set({ isLoading: false });
      }
    },
  }))
);
