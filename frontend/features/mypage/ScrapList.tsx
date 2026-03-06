"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScraps } from "./mypage.api";
import { Scrap } from "./mypage.types";
import { PolicyCardItem } from "../policy/policy.types";
import { PolicyCard } from "../policy/PolicyCard";
import { CATEGORY_NAME_MAP } from "../policy/policy.constants";

export function ScrapList() {
    const [scraps, setScraps] = useState<Scrap[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let alive = true;
        (async () => {
            setLoading(true);
            try {
                const data = await fetchScraps();
                if (alive) setScraps(data);
            } finally {
                if (alive) setLoading(false);
            }
        })();
        return () => { alive = false; };
    }, []);

    // Scrap 타입 -> PolicyCardItem 타입 변환
    const toCardItem = (scrap: Scrap): PolicyCardItem => {
        const mappedCategory = CATEGORY_NAME_MAP[scrap.category] || "welfare";

        return {
            id: scrap.plcy_no,
            title: scrap.plcy_nm,
            summary: scrap.plcy_expln_cn?.slice(0, 100) ?? "내용 없음",
            region: scrap.district,
            category: mappedCategory,
            categories: [mappedCategory],
            isPriority: false,
            content: "",
            posterUrl: scrap.posterUrl,
        };
    };

    if (loading) {
        return <div className="py-20 text-center text-gray-500">불러오는 중...</div>;
    }

    if (scraps.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                <p className="mb-4 text-lg">아직 스크랩한 정책이 없습니다.</p>
                <Link
                    href="/policy"
                    className="rounded-lg bg-blue-900 px-4 py-2 text-sm text-white hover:bg-blue-950"
                >
                    정책 찾아보기
                </Link>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {scraps.map((scrap) => (
                <PolicyCard key={scrap.id} policy={toCardItem(scrap)} />
            ))}
        </div>
    );
}
