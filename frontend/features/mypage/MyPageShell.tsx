// features/mypage/MyPageShell.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function SideItem({ href, label }: { href: string; label: string }) {
    const pathname = usePathname();
    const active = pathname === href;

    return (
        <Link
            href={href}
            className={[
                "flex items-center justify-between rounded-lg px-4 py-3 text-sm transition-colors",
                active ? "bg-blue-50 text-blue-700 font-semibold" : "text-gray-800 hover:bg-gray-50",
            ].join(" ")}
        >
            <span>{label}</span>
            <span className="text-gray-400">›</span>
        </Link>
    );
}

export function MyPageShell({ children }: { children: React.ReactNode }) {
    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* [변경점] Grid 대신 Flex 사용
               1. flex-col: 모바일에서는 세로 배치
               2. md:flex-row: PC(md 이상)에서는 가로 배치 
               3. gap-6: 사이 간격
            */}
            <div className="flex flex-col gap-6 md:flex-row">

                {/* 좌측 패널 
                   1. md:w-[300px]: PC에서 너비 300px 고정
                   2. shrink-0: 공간이 좁아져도 찌그러지지 않음 (중요)
                */}
                <aside
                    className={[
                        "h-[calc(100vh-4rem)] overflow-hidden rounded-2xl border bg-white",
                        // "w-full",                // 모바일: 전체폭
                        "shrink-0",              // ✅ 찌그러짐 방지
                        "md:sticky md:top-6",
                        "md:w-[280px] md:max-w-[280px]", // ✅ PC: 고정폭(둘 다)
                    ].join(" ")}
                >
                    <div className="h-36 bg-gradient-to-br from-purple-100 via-indigo-100 to-pink-100 p-6">
                        <div className="text-2xl font-bold text-gray-900">마이페이지</div>
                    </div>

                    <div className="p-3">
                        <div className="space-y-1">
                            <SideItem href="/mypage" label="마이페이지 홈" />
                            <SideItem href="/mypage/profile" label="내게 맞는 정책" />
                            <SideItem href="/mypage/secure" label="나의정보관리" />
                        </div>

                        <div className="mt-3 border-t pt-3">
                            <Link href="/" className="block rounded-lg px-4 py-3 text-sm text-gray-700 hover:bg-gray-50">
                                홈으로
                            </Link>
                        </div>
                    </div>
                </aside>

                {/* 본문
                   1. flex-1: 남은 공간을 모두 차지
                   2. min-w-0: 내부 컨텐츠가 넘칠 때 레이아웃 깨짐 방지
                */}
                <main className="flex-1 min-w-0">
                    {children}
                </main>
            </div>
        </div>
    );
}