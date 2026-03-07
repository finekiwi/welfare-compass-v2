// stores/chatbot.store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { ChatMessage } from "@/features/chatbot/chatbot.types";
import { chatbotApi } from "@/features/chatbot/chatbot.api";

interface ChatbotState {
  isOpen: boolean;
  isLoading: boolean;
  sessionId: string | null;
  sessionToken: string | null;
  messages: ChatMessage[];

  open: () => Promise<void>;
  close: () => void;
  reset: () => void;

  sendMessage: (content: string) => Promise<void>;
}

export const useChatbotStore = create<ChatbotState>()(
  devtools((set, get) => ({
    isOpen: false,
    isLoading: false,
    sessionId: null,
    sessionToken: null,
    messages: [],

    open: async () => {
      set({ isOpen: true });

      if (get().sessionId) return;

      try {
        set({ isLoading: true });
        const session = await chatbotApi.createSession();
        set({
          sessionId: session.id,
          sessionToken: session.sessionToken ?? null,
          messages: session.messages,
        });
      } catch (error) {
        console.error("Failed to create chat session:", error);
      } finally {
        set({ isLoading: false });
      }
    },

    close: () => set({ isOpen: false }),

    reset: () => {
      set({
        sessionId: null,
        sessionToken: null,
        messages: [],
        isLoading: false,
      });
    },

    sendMessage: async (content: string) => {
      const { sessionId, sessionToken, messages } = get();
      if (!sessionId) return;

      const tempUserMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        createdAt: Date.now(),
      };

      set({
        isLoading: true,
        messages: [...messages, tempUserMsg],
      });

      try {
        const response = await chatbotApi.sendMessage(sessionId, content, sessionToken);

        set((state) => ({
          messages: [
            ...state.messages.slice(0, -1),
            response.userMessage,
            response.assistantMessage,
          ],
        }));
      } catch (error) {
        console.error("Failed to send message:", error);
      } finally {
        set({ isLoading: false });
      }
    },
  }))
);
