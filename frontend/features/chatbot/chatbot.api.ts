import { api } from "@/services/axios";
import type { ChatSessionResponse, SendMessageResponse } from "./chatbot.types";

const BASE_URL = "/api/v1/chat/sessions";
const SESSION_TOKEN_HEADER = "X-Chat-Session-Token";

export const chatbotApi = {
    /** Create session (includes welcome message). */
    createSession: async (): Promise<ChatSessionResponse> => {
        const { data } = await api.post<ChatSessionResponse>(`${BASE_URL}/`);
        return data;
    },

    /** Send a message and receive AI response. */
    sendMessage: async (
        sessionId: string,
        content: string,
        sessionToken?: string | null,
        includeProfile?: boolean,
    ): Promise<SendMessageResponse> => {
        const { data } = await api.post<SendMessageResponse>(
            `${BASE_URL}/${sessionId}/send/`,
            { content, include_profile: includeProfile || false },
            {
                headers: sessionToken ? { [SESSION_TOKEN_HEADER]: sessionToken } : undefined,
            },
        );
        return data;
    },

    /** Get existing session (includes messages). */
    getSession: async (
        sessionId: string,
        sessionToken?: string | null,
    ): Promise<ChatSessionResponse> => {
        const { data } = await api.get<ChatSessionResponse>(
            `${BASE_URL}/${sessionId}/`,
            {
                headers: sessionToken ? { [SESSION_TOKEN_HEADER]: sessionToken } : undefined,
            },
        );
        return data;
    },
};
