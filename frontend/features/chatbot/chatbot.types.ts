// features/chatbot/chatbot.types.ts

export type ChatRole = "user" | "assistant";

export type EligibilityStatus = "eligible" | "ineligible" | "uncertain";

export interface PolicyCard {
  plcy_no: string;
  plcy_nm: string;
  category: string;
  summary: string;
  eligibility: EligibilityStatus;
  ineligible_reasons: string[];
  deadline: string | null;
  dday: number | null;
  apply_url: string | null;
  detail_url: string | null;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
  policies?: PolicyCard[];
}

export interface ChatSessionResponse {
  id: string;
  createdAt: number;
  expiresAt: number;
  messages: ChatMessage[];
  sessionToken?: string;
  hasProfileData?: boolean;
}

export interface SendMessageResponse {
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
}
