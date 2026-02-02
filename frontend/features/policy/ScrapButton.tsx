"use client";

import { useEffect, useState } from "react";
import { addScrap, removeScrap, fetchScraps } from "@/features/mypage/mypage.api";

interface ScrapButtonProps {
    policyId: string;
    className?: string;
}

export function ScrapButton({ policyId, className = "" }: ScrapButtonProps) {
    const [isScrapped, setIsScrapped] = useState(false);
    const [loading, setLoading] = useState(false);

    // 초기 상태 확인
    useEffect(() => {
        let alive = true;
        (async () => {
            try {
                // TODO: 개별 조회 API가 있다면 더 효율적이겠지만, 현재는 목록 조회해서 확인
                // 백엔드에 '내 스크랩 여부' 확인 API가 있으면 좋음.
                // 우선은 fetchScraps()로 목록 가져와서 find. 
                // (성능 이슈 있으면 백엔드 API 추가 요청 필요 -> 이번엔 그냥 진행)
                const scraps = await fetchScraps();
                if (alive) {
                    const found = scraps.find(s => s.plcy_no === policyId);
                    setIsScrapped(!!found);
                }
            } catch (error) {
                console.error("ScrapButton initial check error:", error);
            }
        })();
        return () => { alive = false; };
    }, [policyId]);

    const handleToggle = async (e: React.MouseEvent) => {
        e.preventDefault(); // 링크 이동 방지 if inside Link
        e.stopPropagation();

        if (loading) return;
        setLoading(true);

        try {
            if (isScrapped) {
                const success = await removeScrap(policyId);
                if (success) setIsScrapped(false);
            } else {
                const success = await addScrap(policyId);
                if (success) setIsScrapped(true);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            type="button"
            className={`transition-colors focus:outline-none ${className}`}
            onClick={handleToggle}
            aria-label={isScrapped ? "스크랩 취소" : "스크랩 하기"}
        >
            {isScrapped ? (
                // 꽉 찬 별 (Yellow)
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8 text-yellow-400 drop-shadow-sm">
                    <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006z" clipRule="evenodd" />
                </svg>
            ) : (
                // 빈 별 (Gray)
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-gray-300 hover:text-gray-400">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.563.045.796.756.407 1.134l-4.25 4.148a.563.563 0 00-.165.511l1.19 5.495c.124.576-.51.985-.972.695l-4.823-2.775a.562.562 0 00-.54 0l-4.823 2.775c-.461.29-1.096-.119-.972-.695l1.19-5.495a.563.563 0 00-.165-.511l-4.25-4.148c-.389-.378-.156-1.089.407-1.134l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
                </svg>
            )}
        </button>
    );
}
