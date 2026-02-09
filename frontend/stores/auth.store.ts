// stores/auth.store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";

import { api } from "@/services/axios";
import { logout as logoutApi } from "@/features/auth/auth.api";

interface AuthTokens {
    access: string;
    refresh: string;
}

interface AuthState {
    isAuthenticated: boolean;
    isInitialized: boolean;

    /** 앱 시작 시 쿠키 확인 (실제로는 프로필 조회 API 호출로 검증) */
    initialize: () => Promise<void>;

    /** 로그인 성공 시 상태 업데이트 (쿠키는 서버가 Set-Cookie로 처리) */
    login: (tokens?: AuthTokens) => void;

    /** 로그아웃 시 상태 초기화 (서버에 로그아웃 요청) */
    logout: () => Promise<void>;
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

        login: () => {
            // LocalStorage 관련 로직 제거
            // 쿠키는 브라우저가 알아서 관리
            localStorage.removeItem("welfarecompass:mypage_profile");
            localStorage.removeItem("welfarecompass:verify_state");
            set({ isAuthenticated: true });
        },

        logout: async () => {
            try {
                // 백엔드 로그아웃 API 호출 → 서버가 쿠키를 삭제함
                await logoutApi();
            } catch (error) {
                console.error("Logout API call failed:", error);
            }

            // LocalStorage 관련 로직 제거
            localStorage.removeItem("welfarecompass:mypage_profile");
            localStorage.removeItem("welfarecompass:verify_state");

            set({ isAuthenticated: false });
        },
    }))
);
