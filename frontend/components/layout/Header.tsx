// components/layout/Header.tsx
import Link from "next/link";

export function Header() {
  // ✅ 지금은 정적 헤더(이미지의 상단 네비 느낌만 구현)
  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="inline-block h-8 w-8 rounded-full bg-gray-200" />
          <span>복지나침반</span>
        </Link>

        <nav className="flex items-center gap-6 text-sm text-gray-700">
          <Link href="/policy">복지찾기</Link>
          <Link href="/policy">복지달력</Link>
          <Link href="/policy">복지지도</Link>
          <Link href="/mypage">마이페이지</Link>
        </nav>

        <div className="text-sm text-gray-600">로그인</div>
      </div>
    </header>
  );
}
