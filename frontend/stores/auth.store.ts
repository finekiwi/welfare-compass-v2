// stores/auth.store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";

import { api, apiRaw } from "@/services/axios";
import { useProfileStore } from "./profile.store";
import { useChatbotStore } from "./chatbot.store";

interface AuthTokens {
    access: string;
    refresh: string;
}

interface AuthState {
    isAuthenticated: boolean;
    isInitialized: boolean;

    /** 앱 시작 시 쿠키 확인 (실제로는 프로필 조회 API 호출로 검증) */
    initialize: () => Promise<void>;

    /** 로그인 성공 시 쿠키 검증 후 상태 업데이트 (보수적 업데이트) */
    login: () => Promise<void>;

    /** 로그아웃: 서버 API 호출 + 클라이언트 상태 정리 */
    logout: () => Promise<void>;

    /** 클라이언트 상태만 정리 (서버 호출 없음, 인터셉터 재귀 방지용) */
    clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
    devtools((set) => ({
        isAuthenticated: false,
        isInitialized: false,

        initialize: async () => {
            try {
                // 토큰 유효성 검사를 위해 프로필 API 호출
                await api.get("/api/accounts/profile/");
                set({
                    isAuthenticated: true,
                    isInitialized: true,
                });
            } catch (error) {
                // 401 Unauthorized etc.
                set({
                    isAuthenticated: false,
                    isInitialized: true,
                });
            }
        },

        login: async () => {
            // [보안] 보수적(Pessimistic) 업데이트: 쿠키가 정상 세팅되었는지 프로필 API로 재검증
            localStorage.removeItem("welfarecompass:mypage_profile");
            localStorage.removeItem("welfarecompass:verify_state");
            useChatbotStore.getState().reset();
            // 프로필 검증 실패 시 throw하여 LoginForm의 catch 블록으로 전파
            await api.get("/api/accounts/profile/");
            set({ isAuthenticated: true });
        },

        logout: async () => {
            try {
                // [보안] 인터셉터 없는 apiRaw 사용 → 401이 와도 재귀 호출 없음
                // apiRaw는 CSRF 인터셉터가 없으므로 쿠키에서 직접 읽어 헤더로 추가
                const csrfToken = typeof document !== "undefined"
                    ? document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1]
                    : undefined;

                await apiRaw.post("/api/auth/logout/", {}, {
                    headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
                });
            } catch (error) {
                console.error("Logout API call failed:", error);
            }

            localStorage.removeItem("welfarecompass:mypage_profile");
            localStorage.removeItem("welfarecompass:verify_state");

            useProfileStore.getState().reset();
            useChatbotStore.getState().reset();
            set({ isAuthenticated: false });
        },

        // [보안] 인터셉터에서 호출하는 상태 정리 전용 (서버 호출 없음 → 재귀 불가)
        clearAuth: () => {
            localStorage.removeItem("welfarecompass:mypage_profile");
            localStorage.removeItem("welfarecompass:verify_state");
            useProfileStore.getState().reset();
            useChatbotStore.getState().reset();
            set({ isAuthenticated: false });
        },
    }))
);
