// components/layout/Header.tsx
import Link from "next/link";
import Image from "next/image";

export function Header() {
  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
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

        <nav className="flex items-center gap-6 text-sm text-gray-700">
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

        {/* ✅ 우측: 로그인 / 회원가입 링크 */}
        <div className="flex items-center gap-3 text-sm">
          <Link href="/login" className="text-gray-700 hover:text-gray-900">
            로그인
          </Link>

          {/* 구분선 */}
          <span className="h-4 w-px bg-gray-200" />

          {/* 회원가입은 버튼처럼 보이게 */}
          <Link
            href="/signup"
            className="rounded-md px-3 py-1.5 font-medium hover:bg-blue-700"
          >
            회원가입
          </Link>
        </div>
      </div>
    </header>
  );
}
