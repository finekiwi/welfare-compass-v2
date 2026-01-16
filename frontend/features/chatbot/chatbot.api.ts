import { api } from "@/services/axios";
import type { ChatSessionResponse, SendMessageResponse } from "./chatbot.types";

const BASE_URL = "/api/v1/chat/sessions";

export const chatbotApi = {
    /** 세션 생성 (웰컴 메시지 포함) */
    createSession: async (): Promise<ChatSessionResponse> => {
        const { data } = await api.post<ChatSessionResponse>(`${BASE_URL}/`);
        return data;
    },

    /** 메시지 전송 및 응답 수신 */
    sendMessage: async (
        sessionId: string,
        content: string
    ): Promise<SendMessageResponse> => {
        const { data } = await api.post<SendMessageResponse>(
            `${BASE_URL}/${sessionId}/send/`,
            { content }
        );
        return data;
    },

    /** 세션 조회 (메시지 목록 포함) */
    getSession: async (sessionId: string): Promise<ChatSessionResponse> => {
        const { data } = await api.get<ChatSessionResponse>(
            `${BASE_URL}/${sessionId}/`
        );
        return data;
    },
};
