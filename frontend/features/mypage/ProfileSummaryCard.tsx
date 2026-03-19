"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getMyProfile } from "./mypage.api";
import type { MyProfile } from "./mypage.types";
import {
    JOB_STATUS_TO_API,
    EDUCATION_STATUS_TO_API,
    MARRIAGE_STATUS_TO_API,
} from "@/features/policy/policy.constants";

function Tile({ title, value }: { title: string; value: string }) {
    return (
        <div className="rounded-xl border bg-white p-5 text-center">
            <div className="text-xs text-gray-500">{title}</div>
            <div className="mt-2 text-sm font-semibold text-blue-800">{value}</div>
        </div>
    );
}

function buildPolicyFilterHref(profile: MyProfile, age: number | null): string {
    const params = new URLSearchParams();

    // 지역 강제 필터는 결과 0건을 유발할 수 있어 제외
    const employment = profile.jobStatus ? JOB_STATUS_TO_API[profile.jobStatus] : undefined;
    const education = profile.educationStatus ? EDUCATION_STATUS_TO_API[profile.educationStatus] : undefined;
    const marriage = profile.marriageStatus ? MARRIAGE_STATUS_TO_API[profile.marriageStatus] : undefined;

    if (employment) params.set("employment_status", employment);
    if (education) params.set("education_status", education);
    if (marriage) params.set("marriage_status", marriage);
    if (age && age > 0) params.set("age", String(age));

    const specials = profile.specialConditions || [];
    const hasSpecial = (...keywords: string[]) =>
        specials.some((value) => keywords.some((keyword) => value?.includes(keyword)));

    if (hasSpecial("한부모")) params.set("is_for_single_parent", "true");
    if (hasSpecial("장애", "장애인")) params.set("is_for_disabled", "true");
    if (hasSpecial("기초수급", "기초수급자", "저소득")) params.set("is_for_low_income", "true");
    if (hasSpecial("신혼", "신혼부부")) params.set("is_for_newlywed", "true");

    const query = params.toString();
    return query ? `/policy?${query}` : "/policy";
}

export function ProfileSummaryCard() {
    const [profile, setProfile] = useState<MyProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;
        (async () => {
            try {
                setLoading(true);
                setError(null);
                const data = await getMyProfile();
                if (!alive) return;
                setProfile(data);
            } catch {
                if (!alive) return;
                setError("프로필 정보를 불러오지 못했습니다.");
            } finally {
                if (alive) setLoading(false);
            }
        })();
        return () => {
            alive = false;
        };
    }, []);

    if (loading) {
        return <div className="rounded-2xl border bg-white p-6 text-sm text-gray-600">불러오는 중...</div>;
    }

    if (error) {
        return <div className="rounded-2xl border bg-white p-6 text-sm text-red-600">{error}</div>;
    }

    if (!profile) {
        return <div className="rounded-2xl border bg-white p-6 text-sm text-gray-600">프로필이 없습니다.</div>;
    }

    const age = profile.birthYear ? new Date().getFullYear() - profile.birthYear : null;
    const diagnosisHref = buildPolicyFilterHref(profile, age);
    const diagnosisCount: number | null = null; // TODO: API 연동 시 실제 진단 이력 개수로 교체

    return (
        <div className="space-y-6">
            <div>
                <div className="text-sm text-gray-500">홈 {">"} 마이페이지</div>
                <h1 className="mt-2 text-3xl font-bold">마이페이지</h1>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[420px_1fr]">
                <div className="rounded-2xl bg-gradient-to-b from-indigo-100 via-purple-100 to-pink-100 p-8">
                    <div className="flex flex-col items-center text-center">
                        <div className="mb-4 grid h-28 w-28 place-items-center rounded-full bg-white/70">
                            <Image src={profile.avatarUrl || "/mascot/profile-default.png"} alt="avatar" width={90} height={90} />
                        </div>

                        <div className="text-xl font-bold">
                            <span className="text-blue-800">{profile.displayName}</span>님의 프로필 정보
                        </div>
                        <p className="mt-3 text-sm text-gray-700">개인 정보와 관심 분야를 기반으로 맞춤 정책을 제공합니다.</p>

                        <Link
                            href="/mypage/profile"
                            className="mt-6 inline-flex h-11 w-full max-w-[260px] items-center justify-center rounded-lg bg-purple-700 text-sm font-semibold text-white hover:bg-purple-800"
                        >
                            프로필 정보 수정하기
                        </Link>
                    </div>
                </div>

                <div className="rounded-2xl bg-gray-50 p-6">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        <Tile title="거주지" value={profile.district || "-"} />
                        <Tile title="연령" value={age ? `만 ${age}세` : "-"} />
                        <Tile title="혼인 상태" value={labelMarriage(profile.marriageStatus)} />
                        <Tile title="주거 형태" value={labelHousing(profile.housingType)} />
                        <Tile title="소득 수준" value={labelIncomeLevel(profile.incomeLevel)} />
                        <Tile title="가구원 수" value={profile.householdSize ? `${profile.householdSize}명` : "-"} />

                        <div className="md:col-span-2">
                            <div className="rounded-xl border bg-white p-5 text-center">
                                <div className="text-xs text-gray-500">취업 상태</div>
                                <div className="mt-2 text-sm font-semibold text-blue-800">{labelJob(profile.jobStatus)}</div>
                            </div>
                        </div>

                        <div>
                            <div className="rounded-xl border bg-white p-5 text-center">
                                <div className="text-xs text-gray-500">특수 조건</div>
                                <div className="mt-2 text-sm font-semibold text-blue-800">
                                    {profile.specialConditions && profile.specialConditions.length > 0 ? profile.specialConditions.join(", ") : "-"}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="rounded-2xl border bg-white p-6">
                <div className="text-sm font-semibold">신청자격 진단 결과 조회</div>
                <div className="mt-3 flex items-center justify-between rounded-lg bg-gray-50 p-4">
                    <div className="text-sm text-gray-700">
                        {diagnosisCount == null ? (
                            <>신청자격 진단 이력은 연동 예정입니다.</>
                        ) : (
                            <>
                                총 <span className="font-semibold text-blue-800">{diagnosisCount}</span>건의 신청자격 진단 이력이 있습니다.
                            </>
                        )}
                    </div>
                    <Link href={diagnosisHref} className="rounded-lg bg-gray-900 px-4 py-2 text-xs font-semibold text-white">
                        나의 신청자격진단 바로가기
                    </Link>
                </div>
            </div>
        </div>
    );
}

function labelMarriage(v: string) {
    const map: Record<string, string> = { single: "미혼", married: "기혼", other: "기타" };
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
