// features/auth/components/UserMenu.tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/services/axios";

export function UserMenu() {
    const router = useRouter();
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        // localStorage 체크로 로그인 상태 확인
        const token = localStorage.getItem("access_token");
        setIsLoggedIn(!!token);
    }, []);

    const handleLogout = () => {
        // 1. 토큰 삭제
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");

        // 2. 상태 업데이트
        setIsLoggedIn(false);

        // 3. 메인으로 이동 & 새로고침 (헤더 상태 갱신 확실히 하기 위해)
        // router.push("/") 대신 window.location.href 사용이 더 확실할 수 있음
        window.location.href = "/";
    };

    // Hydration mismatch 방지: 마운트 전에는 아무것도 안 보여줌 (또는 스켈레톤)
    if (!mounted) return null;

    if (isLoggedIn) {
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
