// features/mypage/ProfileSummaryCard.tsx

"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getMyProfile } from "./mypage.api";
import type { MyProfile } from "./mypage.types";

function Tile({ title, value }: { title: string; value: string }) {
    return (
        <div className="rounded-xl border bg-white p-5 text-center">
            <div className="text-xs text-gray-500">{title}</div>
            <div className="mt-2 text-sm font-semibold text-blue-800">{value}</div>
        </div>
    );
}

export function ProfileSummaryCard() {
    const [profile, setProfile] = useState<MyProfile | null>(null);

    useEffect(() => {
        (async () => setProfile(await getMyProfile()))();
    }, []);

    if (!profile) {
        return (
            <div className="rounded-2xl border bg-white p-6 text-sm text-gray-600">
                불러오는 중...
            </div>
        );
    }

    // 나이 계산
    const age = profile.birthYear ? new Date().getFullYear() - profile.birthYear : null;

    return (
        <div className="space-y-6">
            {/* 상단 제목 */}
            <div>
                <div className="text-sm text-gray-500">홈 &gt; 마이페이지</div>
                <h1 className="mt-2 text-3xl font-bold">마이페이지</h1>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[420px_1fr]">
                {/* 좌측 퍼스널 카드(그라데이션) */}
                <div className="rounded-2xl bg-gradient-to-b from-indigo-100 via-purple-100 to-pink-100 p-8">
                    <div className="flex flex-col items-center text-center">
                        <div className="mb-4 grid h-28 w-28 place-items-center rounded-full bg-white/70">
                            {/* 이미지 없으면 간단 원형 */}
                            {profile.avatarUrl ? (
                                <Image src={profile.avatarUrl} alt="avatar" width={70} height={70} />
                            ) : (
                                <div className="h-16 w-16 rounded-full bg-gray-200" />
                            )}
                        </div>

                        <div className="text-xl font-bold">
                            <span className="text-blue-800">{profile.displayName}</span>의 퍼스널 정보
                        </div>
                        <p className="mt-3 text-sm text-gray-700">
                            설정하신 개인정보 및 관심분야를 기반으로 맞춤 정책을 제공합니다.
                        </p>

                        <Link
                            href="/mypage/profile"
                            className="mt-6 inline-flex h-11 w-full max-w-[260px] items-center justify-center rounded-lg bg-purple-700 text-sm font-semibold text-white hover:bg-purple-800"
                        >
                            퍼스널정보 설정하기
                        </Link>
                    </div>
                </div>

                {/* 우측 요약 타일 */}
                <div className="rounded-2xl bg-gray-50 p-6">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        <Tile title="거주지역" value={profile.district || "-"} />
                        <Tile title="연령" value={age ? `만 ${age}세` : "-"} />
                        <Tile title="혼인여부" value={labelMarriage(profile.marriageStatus)} />

                        <Tile title="주거형태" value={labelHousing(profile.housingType)} />
                        <Tile title="소득수준" value={labelIncomeLevel(profile.incomeLevel)} />
                        <Tile title="가구원수" value={profile.householdSize ? `${profile.householdSize}명` : "-"} />

                        <div className="md:col-span-2">
                            <div className="rounded-xl border bg-white p-5 text-center">
                                <div className="text-xs text-gray-500">취업상태</div>
                                <div className="mt-2 text-sm font-semibold text-blue-800">
                                    {labelJob(profile.jobStatus)}
                                </div>
                            </div>
                        </div>

                        <div>
                            <div className="rounded-xl border bg-white p-5 text-center">
                                <div className="text-xs text-gray-500">특수조건</div>
                                <div className="mt-2 text-sm font-semibold text-blue-800">
                                    {profile.specialConditions && profile.specialConditions.length > 0
                                        ? profile.specialConditions.join(", ")
                                        : "-"}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 하단 박스(신청자격진단 현황 느낌) */}
            <div className="rounded-2xl border bg-white p-6">
                <div className="text-sm font-semibold">신청자격진단 결과 현황</div>
                <div className="mt-3 flex items-center justify-between rounded-lg bg-gray-50 p-4">
                    <div className="text-sm text-gray-700">
                        총 <span className="font-semibold text-blue-800">0</span>건의 신청자격진단이력이 있습니다.
                    </div>
                    <Link
                        href="/policy"
                        className="rounded-lg bg-gray-900 px-4 py-2 text-xs font-semibold text-white"
                    >
                        나의 신청자격진단 바로가기
                    </Link>
                </div>
            </div>
        </div>
    );
}

// ---- 라벨 변환(가독성용) ----
function labelMarriage(v: string) {
    const map: Record<string, string> = {
        single: "미혼",
        married: "기혼",
        other: "기타",
    };
    return map[v] ?? "-";
}

function labelHousing(v: string) {
    const map: Record<string, string> = {
        jeonse: "전세",
        monthly: "월세",
        owned: "자가",
        gosiwon: "고시원",
        parents: "부모님집",
        public: "공공임대",
        other: "기타",
    };
    return map[v] ?? "-";
}

function labelIncomeLevel(v: string) {
    const map: Record<string, string> = {
        below_50: "중위 50% 이하",
        below_100: "중위 100% 이하",
        above_100: "중위 100% 초과",
        unknown: "모름",
    };
    return map[v] ?? "-";
}

function labelJob(v: string) {
    const map: Record<string, string> = {
        employed: "재직중",
        unemployed: "미취업",
        job_seeking: "구직중",
        student: "학생",
        startup: "창업준비",
        freelancer: "프리랜서",
        other: "기타",
    };
    return map[v] ?? "-";
}
