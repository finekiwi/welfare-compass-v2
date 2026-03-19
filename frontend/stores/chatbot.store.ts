// stores/chatbot.store.ts
import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";

import { chatbotApi } from "@/features/chatbot/chatbot.api";
import type { ChatMessage } from "@/features/chatbot/chatbot.types";

interface ChatbotState {
  isOpen: boolean;
  isLoading: boolean;
  sessionId: string | null;
  sessionToken: string | null;
  messages: ChatMessage[];
  hasProfileData: boolean;
  profileInjected: boolean;
  panelWidth: number;
  panelHeight: number;
  panelX: number | null;
  panelY: number | null;

  open: () => Promise<void>;
  close: () => void;
  reset: () => void;
  resetConversation: () => Promise<void>;
  ensureSession: () => Promise<void>;
  refreshSession: () => Promise<void>;
  setProfileInjected: (value: boolean) => void;
  setPanelSize: (width: number, height: number) => void;
  setPanelPosition: (x: number, y: number) => void;

  sendMessage: (content: string, includeProfile?: boolean) => Promise<void>;
}

const DEFAULT_PANEL_WIDTH = 420;
const DEFAULT_PANEL_HEIGHT = 620;

function buildAssistantNotice(content: string): ChatMessage {
  return {
    id: crypto.randomUUID?.() ?? Math.random().toString(36).slice(2),
    role: "assistant",
    content,
    createdAt: Date.now(),
  };
}

export const useChatbotStore = create<ChatbotState>()(
  devtools(
    persist(
      (set, get) => ({
        isOpen: false,
        isLoading: false,
        sessionId: null,
        sessionToken: null,
        messages: [],
        hasProfileData: false,
        profileInjected: false,
        panelWidth: DEFAULT_PANEL_WIDTH,
        panelHeight: DEFAULT_PANEL_HEIGHT,
        panelX: null,
        panelY: null,

        open: async () => {
          set({
            isOpen: true,
            panelWidth: DEFAULT_PANEL_WIDTH,
            panelHeight: DEFAULT_PANEL_HEIGHT,
            panelX: null,
            panelY: null,
          });
          await get().ensureSession();
        },

        close: () => set({ isOpen: false, panelX: null, panelY: null }),

        reset: () => {
          set({
            isOpen: false,
            sessionId: null,
            sessionToken: null,
            messages: [],
            isLoading: false,
            profileInjected: false,
          });
        },

        resetConversation: async () => {
          await get().refreshSession();
          set({ isOpen: true });
        },

        ensureSession: async () => {
          if (get().sessionId) return;

          try {
            set({ isLoading: true });
            const session = await chatbotApi.createSession();
            set({
              sessionId: session.id,
              sessionToken: session.sessionToken ?? null,
              messages: session.messages,
              hasProfileData: session.hasProfileData ?? false,
            });
          } catch (error) {
            console.error("Failed to create chat session:", error);
            set({
              messages: [
                buildAssistantNotice("대화 세션을 시작하지 못했습니다. 잠시 후 다시 시도해주세요."),
              ],
            });
          } finally {
            set({ isLoading: false });
          }
        },

        refreshSession: async () => {
          set({
            sessionId: null,
            sessionToken: null,
            messages: [],
            hasProfileData: false,
            profileInjected: false,
            isLoading: false,
          });
          await get().ensureSession();
        },

        setProfileInjected: (value: boolean) => set({ profileInjected: value }),

        setPanelSize: (width: number, height: number) => {
          set({ panelWidth: width, panelHeight: height });
        },

        setPanelPosition: (x: number, y: number) => {
          set({ panelX: x, panelY: y });
        },

        sendMessage: async (content: string, includeProfile?: boolean) => {
          const { sessionId, sessionToken, messages } = get();
          if (!sessionId) return;

          const tempUserMsg: ChatMessage = {
            id: crypto.randomUUID?.() ?? Math.random().toString(36).slice(2),
            role: "user",
            content,
            createdAt: Date.now(),
          };

          set({
            isLoading: true,
            messages: [...messages, tempUserMsg],
          });

          try {
            const response = await chatbotApi.sendMessage(
              sessionId,
              content,
              sessionToken,
              includeProfile,
            );

            const normalizedUserMessage: ChatMessage = {
              ...response.userMessage,
              // UI에는 원문 입력만 노출 (프로필 컨텍스트는 서버 내부 추론용)
              content,
            };

            set((state) => ({
              messages: [
                ...state.messages.slice(0, -1),
                normalizedUserMessage,
                response.assistantMessage,
              ],
            }));
          } catch (error) {
            console.error("Failed to send message:", error);
            set((state) => ({
              messages: [
                ...state.messages.slice(0, -1),
                buildAssistantNotice("메시지 전송에 실패했습니다. 다시 시도해주세요."),
              ],
            }));
          } finally {
            set({ isLoading: false });
          }
        },
      }),
      {
        name: "welfarecompass:chatbot_ui_v2",
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          panelWidth: state.panelWidth,
          panelHeight: state.panelHeight,
          panelX: state.panelX,
          panelY: state.panelY,
        }),
      },
    ),
  ),
);
