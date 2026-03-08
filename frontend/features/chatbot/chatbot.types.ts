// features/chatbot/chatbot.types.ts

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
}

export interface ChatSessionResponse {
  id: string;
  createdAt: number;
  expiresAt: number;
  messages: ChatMessage[];
  sessionToken?: string;
}

export interface SendMessageResponse {
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
}
