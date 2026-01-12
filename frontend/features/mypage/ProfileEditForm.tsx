// features/mypage/ProfileEditForm.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { getMyProfile, saveMyProfile } from "./mypage.api";
import type {
    MyProfile,
    Education,
    JobStatus,
    MajorField,
    SpecialtyField,
    MaritalStatus,
} from "./mypage.types";

const INTEREST_REGIONS = ["서울 종로구 외 24", "서울 전역", "강남구", "마포구", "은평구"];

const EDU_OPTIONS: Array<{ v: Education; label: string }> = [
    { v: "none", label: "제한없음" },
    { v: "lt_high", label: "고졸 미만" },
    { v: "high_in_school", label: "고교 재학" },
    { v: "high_expected", label: "고졸 예정" },
    { v: "high_grad", label: "고교 졸업" },
    { v: "college_in_school", label: "대학 재학" },
    { v: "college_expected", label: "대졸 예정" },
    { v: "college_grad", label: "대학 졸업" },
    { v: "graduate", label: "석·박사" },
    { v: "other", label: "기타" },
];

const JOB_OPTIONS: Array<{ v: JobStatus; label: string }> = [
    { v: "none", label: "제한없음" },
    { v: "worker", label: "재직자" },
    { v: "self_employed", label: "자영업자" },
    { v: "unemployed", label: "미취업자" },
    { v: "freelancer", label: "프리랜서" },
    { v: "daily_worker", label: "일용근로자" },
    { v: "startup_preparing", label: "(예비)창업자" },
    { v: "short_term_worker", label: "단기근로자" },
    { v: "other", label: "기타" },
];

const MAJOR_OPTIONS: Array<{ v: MajorField; label: string }> = [
    { v: "none", label: "제한없음" },
    { v: "humanities", label: "인문계열" },
    { v: "social", label: "사회계열" },
    { v: "business", label: "상경계열" },
    { v: "science", label: "이학계열" },
    { v: "engineering", label: "공학계열" },
    { v: "arts", label: "예체능계열" },
    { v: "agriculture", label: "농산업계열" },
    { v: "other", label: "기타" },
];

const SPECIAL_OPTIONS: Array<{ v: SpecialtyField; label: string }> = [
    { v: "none", label: "제한없음" },
    { v: "sme", label: "중소기업" },
    { v: "women", label: "여성" },
    { v: "basic_living", label: "기초생활수급자" },
    { v: "single_parent", label: "한부모가정" },
    { v: "disabled", label: "장애인" },
    { v: "agriculture", label: "농업인" },
    { v: "military", label: "군인" },
    { v: "local_talent", label: "지역인재" },
    { v: "other", label: "기타" },
];

/**
 * ✅ Chip
 * - 사진처럼 "가로로 길게 눌러 선택" 스타일
 */
function Chip({
    active,
    label,
    onClick,
}: {
    active: boolean;
    label: string;
    onClick: () => void;
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={[
                "h-11 rounded-lg border px-4 text-sm transition",
                active
                    ? "border-blue-600 bg-blue-50 text-blue-700 font-semibold"
                    : "bg-white hover:bg-gray-50",
            ].join(" ")}
        >
            {label}
        </button>
    );
}

export function ProfileEditForm() {
    const [origin, setOrigin] = useState<MyProfile | null>(null);
    const [form, setForm] = useState<MyProfile | null>(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        (async () => {
            const p = await getMyProfile();
            setOrigin(p);
            setForm(p);
        })();
    }, []);

    const dirty = useMemo(() => {
        if (!origin || !form) return false;
        return JSON.stringify(origin) !== JSON.stringify(form);
    }, [origin, form]);

    if (!form) {
        return (
            <div className="rounded-2xl border bg-white p-6 text-sm text-gray-600">
                불러오는 중...
            </div>
        );
    }

    async function onReset() {
        if (!origin) return;
        setForm(origin);
    }

    async function onSave() {
        if (!form) return;
        setSaving(true);
        try {
            await saveMyProfile(form);
            const latest = await getMyProfile();
            setOrigin(latest);
            setForm(latest);
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="text-sm text-gray-500">홈 &gt; 마이페이지 &gt; 내게 맞는 정책</div>
            <h1 className="text-3xl font-bold">내게 맞는 정책</h1>

            {/* ✅ 상단 배너(사진 2번 느낌) */}
            <div className="flex flex-col items-start justify-between gap-4 rounded-2xl bg-[#0b2f6d] p-6 text-white md:flex-row md:items-center">
                <div className="flex items-center gap-4">
                    <div className="grid h-14 w-14 place-items-center rounded-full bg-white/15">
                        <Image
                            src={form.avatarUrl || "/images/beluga.png"}
                            alt="avatar"
                            width={40}
                            height={40}
                            className="object-contain"
                        />
                    </div>
                    <div>
                        <div className="text-lg font-bold">{form.displayName}의 퍼스널 정보</div>
                        <div className="mt-1 text-sm text-white/80">
                            설정하신 개인정보 및 관심분야를 기반으로 맞춤 정책을 제공합니다.
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={onReset}
                        className="h-10 rounded-lg bg-white px-4 text-sm font-semibold text-[#0b2f6d]"
                    >
                        초기화
                    </button>
                    <button
                        type="button"
                        onClick={onSave}
                        disabled={!dirty || saving}
                        className={[
                            "h-10 rounded-lg border px-4 text-sm font-semibold transition",
                            !dirty || saving
                                ? "cursor-not-allowed border-white/30 text-white/50"
                                : "border-white text-white hover:bg-white/10",
                        ].join(" ")}
                    >
                        {saving ? "저장 중..." : "변경사항 저장하기"}
                    </button>
                </div>
            </div>

            {/* ✅ 그리드: 사진처럼 배치 */}
            <div className="grid grid-cols-1 items-stretch gap-6 md:grid-cols-3">
                {/* 1행: 관심지역 / 연령 / 혼인여부 */}
                <Card
                    title="관심지역"
                    right={
                        <span className="rounded-md bg-gray-900 px-3 py-1 text-xs font-semibold text-white">
                            선택
                        </span>
                    }
                >
                    <select
                        value={form.interestDistrict}
                        onChange={(e) => setForm({ ...form, interestDistrict: e.target.value })}
                        className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                    >
                        {INTEREST_REGIONS.map((r) => (
                            <option key={r} value={r}>
                                {r}
                            </option>
                        ))}
                    </select>
                </Card>

                <Card title="연령" right={<button type="button" className="text-gray-400">⟳</button>}>
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">만</span>
                        <input
                            type="number"
                            value={form.age ?? ""}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    age: e.target.value === "" ? null : Number(e.target.value),
                                })
                            }
                            className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            min={0}
                            max={120}
                        />
                        <span className="text-sm text-gray-600">세</span>
                    </div>
                </Card>

                <Card title="혼인여부">
                    <div className="flex flex-wrap gap-2">
                        <Chip
                            active={form.maritalStatus === "none"}
                            label="제한없음"
                            onClick={() => setForm({ ...form, maritalStatus: "none" as MaritalStatus })}
                        />
                        <Chip
                            active={form.maritalStatus === "married"}
                            label="기혼"
                            onClick={() => setForm({ ...form, maritalStatus: "married" as MaritalStatus })}
                        />
                        <Chip
                            active={form.maritalStatus === "single"}
                            label="미혼"
                            onClick={() => setForm({ ...form, maritalStatus: "single" as MaritalStatus })}
                        />
                    </div>
                </Card>

                {/* 2행: ✅ 연소득(2칸) + 학력(1칸) */}
                <Card title="연소득" className="md:col-span-2">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                            <span>연</span>
                            <input
                                type="number"
                                value={form.incomeMin ?? ""}
                                onChange={(e) =>
                                    setForm({
                                        ...form,
                                        incomeMin: e.target.value === "" ? null : Number(e.target.value),
                                    })
                                }
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                            <span>만원 이상 ~</span>
                        </div>

                        <div className="flex items-center gap-2 text-sm text-gray-600">
                            <input
                                type="number"
                                value={form.incomeMax ?? ""}
                                onChange={(e) =>
                                    setForm({
                                        ...form,
                                        incomeMax: e.target.value === "" ? null : Number(e.target.value),
                                    })
                                }
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                            <span>만원 이하</span>
                        </div>
                    </div>
                </Card>

                <Card title="학력" right={<button type="button" className="text-gray-400">⟳</button>} className="md:col-span-1">
                    <div className="flex flex-wrap gap-2">
                        {EDU_OPTIONS.map((o) => (
                            <Chip
                                key={o.v}
                                active={form.education === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, education: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                {/* 3행: 취업상태 / 전공 분야 / 특화 분야 */}
                <Card title="취업상태" right={<button type="button" className="text-gray-400">⟳</button>}>
                    <div className="flex flex-wrap gap-2">
                        {JOB_OPTIONS.map((o) => (
                            <SquarePick
                                key={o.v}
                                active={form.jobStatus === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, jobStatus: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                <Card title="전공 분야" right={<button type="button" className="text-gray-400">⟳</button>}>
                    <div className="flex flex-wrap gap-2">
                        {MAJOR_OPTIONS.map((o) => (
                            <SquarePick
                                key={o.v}
                                active={form.majorField === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, majorField: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                <Card title="특화 분야" right={<button type="button" className="text-gray-400">⟳</button>}>
                    <div className="flex flex-wrap gap-2">
                        {SPECIAL_OPTIONS.map((o) => (
                            <SquarePick
                                key={o.v}
                                active={form.specialtyField === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, specialtyField: o.v })}
                            />
                        ))}
                    </div>
                </Card>
            </div>

            <div className="flex justify-end">
                <Link href="/mypage" className="text-sm text-gray-600 hover:underline">
                    마이페이지로 돌아가기
                </Link>
            </div>
        </div>
    );
}

/**
 * ✅ Card
 * - 사진처럼 "연한 회색 배경 + 둥근 모서리"
 * - h-full: 같은 행에서 카드 높이 균일하게 보이도록
 */
function Card({
    title,
    children,
    right,
    className = "",
}: {
    title: string;
    children: React.ReactNode;
    right?: React.ReactNode;
    className?: string;
}) {
    return (
        <section className={`h-full rounded-2xl bg-gray-50 p-6 ${className}`}>
            <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-bold text-[#0b2f6d]">{title}</h2>
                {right ?? null}
            </div>
            {children}
        </section>
    );
}

/**
 * ✅ SquarePick
 * - 사진처럼 "정사각형 선택 카드"
 * - h-24~h-28 사이가 가장 비슷(지금은 24 유지)
 */
function SquarePick({
    active,
    label,
    onClick,
}: {
    active: boolean;
    label: string;
    onClick: () => void;
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={[
                "h-24 rounded-xl border bg-white p-3 text-sm transition",
                active
                    ? "border-blue-600 bg-blue-50 text-blue-700 font-semibold"
                    : "hover:bg-gray-50",
            ].join(" ")}
        >
            <div className="grid h-full place-items-center">
                <span className="text-center leading-snug">{label}</span>
            </div>
        </button>
    );
}
