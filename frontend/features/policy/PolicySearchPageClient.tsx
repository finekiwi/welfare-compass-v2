// features/policy/PolicySearchPageClient.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchPolicies } from "./policy.api";
import { Policy, PolicyCategory } from "./policy.types";
import { PolicyCard } from "./PolicyCard";

const CATEGORY_OPTIONS: Array<{ value: PolicyCategory | "all"; label: string }> = [
    { value: "all", label: "전체" },
    { value: "housing", label: "주거" },
    { value: "finance", label: "생활·금융" },
    { value: "job", label: "일자리" },
    { value: "entrepreneurship", label: "창업" },
    { value: "mental-health", label: "정신건강" },
    { value: "emotional-wellbeing", label: "마음건강" },
    { value: "care-protection", label: "보호·돌봄" },
];

export function PolicySearchPageClient() {
    const [q, setQ] = useState("");
    const [category, setCategory] = useState<PolicyCategory | "all">("all");
    const [region, setRegion] = useState("서울시");
    const [items, setItems] = useState<Policy[]>([]);
    const [loading, setLoading] = useState(false);

    // ✅ 최초 1회 로드 + 검색 조건 변경 시 로드
    useEffect(() => {
        let alive = true;

        (async () => {
            setLoading(true);
            try {
                const list = await fetchPolicies({ q, category, region });
                if (alive) setItems(list);
            } finally {
                if (alive) setLoading(false);
            }
        })();

        return () => {
            alive = false;
        };
    }, [q, category, region]);

    const countText = useMemo(() => {
        if (loading) return "불러오는 중...";
        return `총 ${items.length}건`;
    }, [items.length, loading]);

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* ✅ 상단 검색 바 (스크린샷 느낌: 버튼 + 셀렉트 + 인풋 + 검색버튼) */}
            <section className="mb-8">
                <div className="flex w-full items-center gap-2 rounded-xl border bg-white p-3">
                    <button
                        type="button"
                        className="rounded-lg bg-gray-800 px-3 py-2 text-xs text-white"
                        onClick={() => {
                            // TODO: 맞춤형 검색 팝업/로그인 연동 등
                            console.log("맞춤형 검색");
                        }}
                    >
                        맞춤형 검색하기
                    </button>

                    {/* region - 지금은 간단 */}
                    <select
                        className="h-9 rounded-lg border px-2 text-xs text-gray-700"
                        value={region}
                        onChange={(e) => setRegion(e.target.value)}
                    >
                        <option value="서울시">서울시</option>
                        <option value="전국">전국</option>
                    </select>

                    {/* category */}
                    <select
                        className="h-9 rounded-lg border px-2 text-xs text-gray-700"
                        value={category}
                        onChange={(e) => setCategory(e.target.value as any)}
                    >
                        {CATEGORY_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>

                    {/* keyword */}
                    <input
                        className="h-9 flex-1 rounded-lg border px-3 text-xs outline-none"
                        placeholder="정책명을 입력해주세요."
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                    />

                    <button
                        type="button"
                        className="h-9 rounded-lg bg-gray-800 px-4 text-xs text-white"
                        onClick={() => {
                            // ✅ 이미 q/category/region 변경 시 자동 검색되지만,
                            // 버튼 UX가 필요하니 남겨둠(필요하면 debounce 적용)
                            console.log("검색");
                        }}
                    >
                        검색
                    </button>
                </div>

                <div className="mt-2 w-full text-right text-[11px] text-gray-500">
                    {countText}
                </div>
            </section>

            {/* ✅ 카드 리스트 */}
            <section className="w-full">
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    {items.map((p) => (
                        <PolicyCard key={p.id} policy={p} />
                    ))}
                </div>

                {!loading && items.length === 0 && (
                    <div className="mt-10 text-center text-sm text-gray-500">
                        조건에 맞는 정책이 없습니다.
                    </div>
                )}
            </section>
        </div>
    );
}
