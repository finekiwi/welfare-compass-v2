"use client";

import Link from "next/link";
import Image from "next/image";
import { UserMenu } from "@/features/auth/components/UserMenu";
import { FontSizeControl } from "@/components/common/FontSizeControl";
import { useAuthStore } from "@/stores/auth.store";
import { useEffect } from "react";

export function Header() {
  const { isAuthenticated, isInitialized, initialize } = useAuthStore();

  useEffect(() => {
    if (!isInitialized) {
      initialize();
    }
  }, [isInitialized, initialize]);

  return (
    <header className="bg-white">
      {/* ✅ 접근성 탑바 (글자 크기 조절) */}
      <div className="border-b border-gray-100 bg-gray-50">
        <div className="mx-auto flex h-9 max-w-[1280px] items-center justify-end px-4">
          <FontSizeControl />
        </div>
      </div>

      {/* ✅ 메인 헤더 */}
      <div className="border-b border-gray-200 mb-3 mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/logo/welfarecompass.png"
            alt="복지나침반 로고"
            width={36}
            height={36}
            className="h-9 w-9 object-contain"
            priority
          />
          <div className="flex flex-col leading-tight">
            <span className="text-base md:text-lg font-bold text-gray-900">복지나침반</span>
            <span className="text-[10px] md:text-[11px] font-medium text-gray-400 tracking-wider">welfarecompass</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1 md:gap-10 text-[13px] md:text-[15px] font-semibold text-gray-800">
          <Link href="/policy" className="hover:text-gray-900">
            복지찾기
          </Link>
          <Link href="/calendar" className="hover:text-gray-900">
            복지달력
          </Link>
          <Link href="/map" className="hover:text-gray-900">
            복지지도
          </Link>
          {isAuthenticated && (
            <Link href="/mypage" className="hover:text-gray-900">
              마이페이지
            </Link>
          )}
        </nav>

        {/* ✅ 우측: 로그인 / 회원가입 */}
        <div className="flex items-center gap-3">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
