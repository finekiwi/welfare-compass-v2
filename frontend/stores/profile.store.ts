// stores/profile.store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { MyProfile } from "@/features/mypage/mypage.types";
import { getMyProfile } from "@/features/mypage/mypage.api";

interface ProfileState {
    profile: MyProfile | null;
    isLoading: boolean;
    error: string | null;

    /** 프로필 불러오기 */
    fetchProfile: () => Promise<void>;

    /** 프로필 저장 (저장 후 store도 동기화) */
    updateProfile: (profile: MyProfile) => Promise<void>;

    /** store 초기화 */
    reset: () => void;
}

export const useProfileStore = create<ProfileState>()(
    devtools((set) => ({
        profile: null,
        isLoading: false,
        error: null,

        fetchProfile: async () => {
            set({ isLoading: true, error: null });
            try {
                const profile = await getMyProfile();
                set({ profile, isLoading: false });
            } catch (error) {
                console.error("Failed to fetch profile:", error);
                set({ error: "프로필을 불러오는데 실패했습니다.", isLoading: false });
            }
        },

        updateProfile: async (profile: MyProfile) => {
            // store 상태만 업데이트 (API 저장은 호출하는 쪽에서 이미 처리)
            set({ profile, isLoading: false, error: null });
        },

        reset: () => {
            set({ profile: null, isLoading: false, error: null });
        },
    }))
);
