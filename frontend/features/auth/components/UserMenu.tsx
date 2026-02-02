// features/auth/components/UserMenu.tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/auth.store";

export function UserMenu() {
    const router = useRouter();
    const { isAuthenticated, isInitialized, initialize, logout } = useAuthStore();

    // 컴포넌트 마운트 시 인증 상태 초기화
    useEffect(() => {
        if (!isInitialized) {
            initialize();
        }
    }, [isInitialized, initialize]);

    const handleLogout = () => {
        logout();
        router.push("/");
    };

    // Hydration mismatch 방지: 초기화 전에는 아무것도 안 보여줌
    if (!isInitialized) return null;

    if (isAuthenticated) {
        return (
            <div className="flex items-center gap-1 md:gap-3 text-xs md:text-sm text-gray-700">
                <Link href="/mypage" className="hover:text-gray-900 font-medium">
                    마이페이지
                </Link>
                <span className="h-4 w-px bg-gray-200" />
                <button
                    onClick={handleLogout}
                    className="hover:text-gray-900"
                >
                    로그아웃
                </button>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-1 md:gap-3 text-xs md:text-sm">
            <Link href="/login" className="text-gray-900 hover:text-black">
                로그인
            </Link>

            <span className="h-4 w-px bg-gray-200" />

            <Link
                href="/signup"
                className="rounded-md px-1 md:px-2 py-1.5 font-medium text-gray-700 transition hover:text-black"
            >
                회원가입
            </Link>
        </div>
    );
}
