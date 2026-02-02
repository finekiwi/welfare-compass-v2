"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { MyPageShell } from "@/features/mypage/MyPageShell";
import { useAuthStore } from "@/stores/auth.store";

export default function MyPageLayout({ children }: { children: ReactNode }) {
    const router = useRouter();
    const { isAuthenticated, isInitialized, initialize } = useAuthStore();

    useEffect(() => {
        if (!isInitialized) {
            initialize();
        }
    }, [isInitialized, initialize]);

    useEffect(() => {
        // 초기화가 완료되었는데 로그인이 안되어있으면 로그인 페이지로 리다이렉트
        if (isInitialized && !isAuthenticated) {
            router.replace("/login");
        }
    }, [isInitialized, isAuthenticated, router]);

    // 인증 체크 중이거나 비로그인 상태면 내용 숨김 (리다이렉트 될 때까지 깜빡임 방지)
    if (!isInitialized || !isAuthenticated) {
        return null;
    }

    // ✅ mypage 이하 모든 라우트(/mypage, /mypage/profile, /mypage/secure, /mypage/verify)가
    //    동일한 왼쪽 메뉴 + 오른쪽 본문 레이아웃을 공유하게 됨
    return <MyPageShell>{children}</MyPageShell>;
}