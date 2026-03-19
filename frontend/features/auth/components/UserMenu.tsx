// features/auth/components/UserMenu.tsx
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/auth.store";

export function UserMenu() {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isInitialized, initialize, logout } = useAuthStore();
  const hideDesktopLoginOnHome = pathname === "/";

  useEffect(() => {
    if (!isInitialized) {
      initialize();
    }
  }, [isInitialized, initialize]);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  if (!isInitialized) return null;

  if (isAuthenticated) {
    return (
      <div className="flex items-center gap-1 text-[12px] text-gray-700 md:gap-3 md:text-[13px]">
        <Link
          href="/mypage"
          className="px-1 py-1.5 transition hover:text-black font-medium"
        >
          마이페이지
        </Link>
        <span className="h-4 w-px bg-gray-200" />
        <button
          onClick={handleLogout}
          className="px-1 py-1.5 transition hover:text-black"
        >
          로그아웃
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 text-[12px] text-gray-700 md:gap-3 md:text-[13px]">
      <Link
        href="/login"
        className={`px-1 py-1.5 transition hover:text-black font-medium ${hideDesktopLoginOnHome ? "lg:hidden" : ""}`}
      >
        로그인
      </Link>

      <span className={`h-4 w-px bg-gray-200 ${hideDesktopLoginOnHome ? "lg:hidden" : ""}`} />

      <Link
        href="/signup"
        className="px-1 py-1.5 transition hover:text-black"
      >
        회원가입
      </Link>
    </div>
  );
}
