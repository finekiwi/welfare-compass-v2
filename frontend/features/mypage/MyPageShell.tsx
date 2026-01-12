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
                "flex items-center justify-between rounded-lg px-4 py-3 text-sm",
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
            <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
                {/* 좌측 패널 */}
                <aside className="h-fit overflow-hidden rounded-2xl border bg-white md:col-span-3 md:sticky md:top-6">
                    <div className="h-36 bg-gradient-to-br from-purple-100 via-indigo-100 to-pink-100 p-6">
                        <div className="text-2xl font-bold text-gray-900">마이페이지</div>
                    </div>

                    <div className="p-3">
                        <div className="space-y-1">
                            <SideItem href="/mypage" label="마이페이지 홈" />
                            <SideItem href="/mypage/profile" label="내게 맞는 정책(퍼스널 정보)" />
                            <SideItem href="/mypage/secure" label="나의정보관리(중요정보)" />
                        </div>

                        <div className="mt-3 border-t pt-3">
                            <Link href="/" className="block rounded-lg px-4 py-3 text-sm text-gray-700 hover:bg-gray-50">
                                홈으로
                            </Link>
                        </div>
                    </div>
                </aside>

                {/* 본문 */}
                <main className="min-w-0 md:col-span-9">{children}</main>
            </div>
        </div>
    );
}
