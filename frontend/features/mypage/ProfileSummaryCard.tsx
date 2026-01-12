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
            <div className="mt-2 text-sm font-semibold text-blue-700">{value}</div>
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
                            <span className="text-blue-700">{profile.displayName}</span>의 퍼스널 정보
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
                        <Tile title="관심지역" value={profile.interestDistrict || "-"} />
                        <Tile title="연령" value={profile.age ? `${profile.age}세` : "-"} />
                        <Tile title="혼인여부" value={profile.maritalStatus === "single" ? "미혼" : profile.maritalStatus === "married" ? "기혼" : "-"} />

                        <Tile title="연소득(만원)" value={profile.incomeMin || profile.incomeMax ? `${profile.incomeMin ?? "-"} ~ ${profile.incomeMax ?? "-"}` : "-"} />
                        <Tile title="학력" value={labelEducation(profile.education)} />
                        <Tile title="전공분야" value={labelMajor(profile.majorField)} />

                        <div className="md:col-span-2">
                            <div className="rounded-xl border bg-white p-5 text-center">
                                <div className="text-xs text-gray-500">취업상태</div>
                                <div className="mt-2 text-sm font-semibold text-blue-700">
                                    {labelJob(profile.jobStatus)}
                                </div>
                            </div>
                        </div>

                        <div>
                            <div className="rounded-xl border bg-white p-5 text-center">
                                <div className="text-xs text-gray-500">특화분야</div>
                                <div className="mt-2 text-sm font-semibold text-blue-700">
                                    {labelSpecial(profile.specialtyField)}
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
                        총 <span className="font-semibold text-blue-700">0</span>건의 신청자격진단이력이 있습니다.
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
function labelEducation(v: any) {
    const map: Record<string, string> = {
        none: "-",
        lt_high: "고졸 미만",
        high_in_school: "고교 재학",
        high_expected: "고졸 예정",
        high_grad: "고교 졸업",
        college_in_school: "대학 재학",
        college_expected: "대졸 예정",
        college_grad: "대학 졸업",
        graduate: "석·박사",
        other: "기타",
    };
    return map[v] ?? "-";
}
function labelJob(v: any) {
    const map: Record<string, string> = {
        none: "-",
        worker: "재직자",
        self_employed: "자영업자",
        unemployed: "미취업자",
        freelancer: "프리랜서",
        daily_worker: "일용근로자",
        startup_preparing: "(예비)창업자",
        short_term_worker: "단기근로자",
        agriculture: "농업인",
        military: "군인",
        local_talent: "지역인재",
        other: "기타",
    };
    return map[v] ?? "-";
}
function labelMajor(v: any) {
    const map: Record<string, string> = {
        none: "-",
        humanities: "인문계열",
        social: "사회계열",
        business: "상경계열",
        science: "이학계열",
        engineering: "공학계열",
        arts: "예체능계열",
        agriculture: "농산업계열",
        other: "기타",
    };
    return map[v] ?? "-";
}
function labelSpecial(v: any) {
    const map: Record<string, string> = {
        none: "-",
        sme: "중소기업",
        women: "여성",
        basic_living: "기초생활수급자",
        single_parent: "한부모가정",
        disabled: "장애인",
        agriculture: "농업인",
        military: "군인",
        local_talent: "지역인재",
        other: "기타",
    };
    return map[v] ?? "-";
}
