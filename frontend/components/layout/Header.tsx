// components/layout/Header.tsx
import Link from "next/link";
import Image from "next/image";
import { UserMenu } from "@/features/auth/components/UserMenu";

export function Header() {
  return (
    <header className="bg-white">
      <div className="border-b border-gray-200 mb-3 mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-sm md:text-lg font-semibold">
          <Image
            src="/logo/welfarecompass.png"
            alt="복지나침반 로고"
            width={32}
            height={32}
            className="h-8 w-8 object-contain"
            priority
          />
          <span>복지나침반</span>
        </Link>

        <nav className="flex items-center gap-1 md:gap-6 text-[13px] md:text-[15px] font-medium text-gray-700">
          <Link href="/policy" className="hover:text-gray-900">
            복지찾기
          </Link>
          <Link href="/calendar" className="hover:text-gray-900">
            복지달력
          </Link>
          <Link href="/map" className="hover:text-gray-900">
            복지지도
          </Link>
          <Link href="/mypage" className="hover:text-gray-900">
            마이페이지
          </Link>
        </nav>

        {/* ✅ 우측: 로그인 / 회원가입 (클라이언트 컴포넌트) */}
        <UserMenu />
      </div>
    </header>
  );
}
