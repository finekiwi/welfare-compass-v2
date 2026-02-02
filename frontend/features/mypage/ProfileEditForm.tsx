// features/mypage/ProfileEditForm.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { getMyProfile, saveMyProfile } from "./mypage.api";
import { useProfileStore } from "@/stores/profile.store";
import type {
    MyProfile,
    JobStatus,
    EducationStatus,
    MarriageStatus,
    IncomeLevel,
    HousingType,
    SpecialCondition,
    NeedCategory,
} from "./mypage.types";
import { SEOUL_DISTRICTS } from "./mypage.types";

// =========================================================================
// 옵션 정의 (Backend choices와 동일)
// =========================================================================

const JOB_OPTIONS: Array<{ v: JobStatus; label: string }> = [
    { v: "employed", label: "재직중" },
    { v: "unemployed", label: "미취업" },
    { v: "job_seeking", label: "구직중" },
    { v: "student", label: "학생" },
    { v: "startup", label: "창업준비" },
    { v: "freelancer", label: "프리랜서" },
    { v: "other", label: "기타" },
];

const EDUCATION_OPTIONS: Array<{ v: EducationStatus; label: string }> = [
    { v: "enrolled", label: "재학" },
    { v: "on_leave", label: "휴학" },
    { v: "graduated", label: "졸업" },
    { v: "dropout", label: "중퇴" },
    { v: "other", label: "기타" },
];

const MARRIAGE_OPTIONS: Array<{ v: MarriageStatus; label: string }> = [
    { v: "single", label: "미혼" },
    { v: "married", label: "기혼" },
    { v: "other", label: "기타" },
];

const INCOME_LEVEL_OPTIONS: Array<{ v: IncomeLevel; label: string }> = [
    { v: "below_50", label: "기준중위소득 50% 이하" },
    { v: "below_100", label: "기준중위소득 100% 이하" },
    { v: "above_100", label: "기준중위소득 100% 초과" },
    { v: "unknown", label: "모름" },
];

const HOUSING_OPTIONS: Array<{ v: HousingType; label: string }> = [
    { v: "jeonse", label: "전세" },
    { v: "monthly", label: "월세" },
    { v: "owned", label: "자가" },
    { v: "gosiwon", label: "고시원" },
    { v: "parents", label: "부모님집" },
    { v: "public", label: "공공임대" },
    { v: "other", label: "기타" },
];

const SPECIAL_CONDITION_OPTIONS: Array<{ v: SpecialCondition; label: string }> = [
    { v: "신혼", label: "신혼부부" },
    { v: "한부모", label: "한부모가정" },
    { v: "장애인", label: "장애인" },
    { v: "기초수급자", label: "기초수급자" },
];

const NEED_OPTIONS: Array<{ v: NeedCategory; label: string }> = [
    { v: "주거", label: "주거" },
    { v: "일자리", label: "일자리" },
    { v: "복지문화", label: "복지/문화" },
    { v: "교육", label: "교육" },
    { v: "건강", label: "건강" },
];

// =========================================================================
// 컴포넌트
// =========================================================================

function Chip({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={[
                "h-11 rounded-lg border px-4 text-sm transition",
                active
                    ? "border-blue-800 bg-blue-50 text-blue-800 font-semibold"
                    : "bg-white hover:bg-gray-50",
            ].join(" ")}
        >
            {label}
        </button>
    );
}

function MultiSelectChip({
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
                "h-10 rounded-lg border px-3 text-sm transition flex items-center gap-1",
                active
                    ? "border-blue-800 bg-blue-50 text-blue-800 font-semibold"
                    : "bg-white hover:bg-gray-50",
            ].join(" ")}
        >
            {active && <span>✓</span>}
            {label}
        </button>
    );
}

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

// =========================================================================
// 메인 폼
// =========================================================================

export function ProfileEditForm() {
    const [origin, setOrigin] = useState<MyProfile | null>(null);
    const [form, setForm] = useState<MyProfile | null>(null);
    const [saving, setSaving] = useState(false);
    const updateProfile = useProfileStore((s) => s.updateProfile);

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

    function toggleSpecialCondition(condition: SpecialCondition) {
        if (!form) return;
        const current = form.specialConditions || [];
        const exists = current.includes(condition);
        setForm({
            ...form,
            specialConditions: exists
                ? current.filter((c) => c !== condition)
                : [...current, condition],
        });
    }

    function toggleNeed(need: NeedCategory) {
        if (!form) return;
        const current = form.needs || [];
        const exists = current.includes(need);
        setForm({
            ...form,
            needs: exists ? current.filter((n) => n !== need) : [...current, need],
        });
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
            await updateProfile(latest);
        } finally {
            setSaving(false);
        }
    }

    // 현재 나이 계산
    const currentAge = form.birthYear ? new Date().getFullYear() - form.birthYear : null;

    return (
        <div className="space-y-6">
            <div className="text-sm text-gray-500">홈 &gt; 마이페이지 &gt; 내게 맞는 정책</div>
            <h1 className="text-3xl font-bold">내게 맞는 정책</h1>

            {/* 상단 배너 */}
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

            {/* 그리드 레이아웃 */}
            <div className="grid grid-cols-1 items-stretch gap-6 md:grid-cols-3">
                {/* ===== 1행: 거주지역 / 출생년도 / 혼인여부 ===== */}
                <Card title="거주지역">
                    <select
                        value={form.district}
                        onChange={(e) => setForm({ ...form, district: e.target.value })}
                        className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                    >
                        <option value="">선택하세요</option>
                        {SEOUL_DISTRICTS.map((d) => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>
                </Card>

                <Card title="출생년도">
                    <div className="flex items-center gap-2">
                        <input
                            type="number"
                            value={form.birthYear ?? ""}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    birthYear: e.target.value === "" ? null : Number(e.target.value),
                                })
                            }
                            placeholder="예: 1998"
                            className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            min={1950}
                            max={2010}
                        />
                        {currentAge && (
                            <span className="whitespace-nowrap text-sm text-gray-500">
                                (만 {currentAge}세)
                            </span>
                        )}
                    </div>
                </Card>

                <Card title="혼인 상태">
                    <div className="flex flex-wrap gap-2">
                        {MARRIAGE_OPTIONS.map((o) => (
                            <Chip
                                key={o.v}
                                active={form.marriageStatus === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, marriageStatus: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                {/* ===== 2행: 주거형태 / 가구원수 / 소득수준 ===== */}
                <Card title="주거형태">
                    <div className="flex flex-wrap gap-2">
                        {HOUSING_OPTIONS.map((o) => (
                            <Chip
                                key={o.v}
                                active={form.housingType === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, housingType: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                <Card title="가구원 수">
                    <div className="flex items-center gap-2">
                        <input
                            type="number"
                            value={form.householdSize ?? ""}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    householdSize: e.target.value === "" ? null : Number(e.target.value),
                                })
                            }
                            placeholder="본인 포함"
                            className="h-11 w-24 rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            min={1}
                            max={10}
                        />
                        <span className="text-sm text-gray-600">명 (본인 포함)</span>
                    </div>
                </Card>

                <Card title="소득 수준">
                    <select
                        value={form.incomeLevel}
                        onChange={(e) => setForm({ ...form, incomeLevel: e.target.value as IncomeLevel })}
                        className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                    >
                        <option value="">선택하세요</option>
                        {INCOME_LEVEL_OPTIONS.map((o) => (
                            <option key={o.v} value={o.v}>{o.label}</option>
                        ))}
                    </select>
                    <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
                        <span>월 소득</span>
                        <input
                            type="number"
                            value={form.incomeAmount ?? ""}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    incomeAmount: e.target.value === "" ? null : Number(e.target.value),
                                })
                            }
                            placeholder="선택"
                            className="h-9 w-24 rounded-lg border px-2 text-sm outline-none focus:border-gray-900"
                        />
                        <span>만원</span>
                    </div>
                </Card>

                {/* ===== 3행: 취업상태 / 학력상태 / 자녀정보 ===== */}
                <Card title="취업 상태">
                    <div className="flex flex-wrap gap-2">
                        {JOB_OPTIONS.map((o) => (
                            <Chip
                                key={o.v}
                                active={form.jobStatus === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, jobStatus: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                <Card title="학력 상태">
                    <div className="flex flex-wrap gap-2">
                        {EDUCATION_OPTIONS.map((o) => (
                            <Chip
                                key={o.v}
                                active={form.educationStatus === o.v}
                                label={o.label}
                                onClick={() => setForm({ ...form, educationStatus: o.v })}
                            />
                        ))}
                    </div>
                </Card>

                <Card title="자녀 정보">
                    <div className="space-y-3">
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={form.hasChildren}
                                    onChange={(e) =>
                                        setForm({
                                            ...form,
                                            hasChildren: e.target.checked,
                                            childrenAges: e.target.checked ? form.childrenAges : [],
                                        })
                                    }
                                    className="h-5 w-5 rounded border-gray-300"
                                />
                                <span className="text-sm">자녀 있음</span>
                            </label>
                        </div>
                        {form.hasChildren && (
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                                <span>자녀 나이:</span>
                                <input
                                    type="text"
                                    value={(form.childrenAges || []).join(", ")}
                                    onChange={(e) => {
                                        const ages = e.target.value
                                            .split(",")
                                            .map((s) => parseInt(s.trim()))
                                            .filter((n) => !isNaN(n));
                                        setForm({ ...form, childrenAges: ages });
                                    }}
                                    placeholder="예: 5, 8"
                                    className="h-9 flex-1 rounded-lg border px-2 text-sm outline-none focus:border-gray-900"
                                />
                            </div>
                        )}
                    </div>
                </Card>

                {/* ===== 4행: 특수조건 (2칸) / 필요분야 (1칸) ===== */}
                <Card title="특수 조건" className="md:col-span-2">
                    <p className="mb-3 text-sm text-gray-500">해당하는 조건을 모두 선택하세요</p>
                    <div className="flex flex-wrap gap-2">
                        {SPECIAL_CONDITION_OPTIONS.map((o) => (
                            <MultiSelectChip
                                key={o.v}
                                active={form.specialConditions?.includes(o.v) ?? false}
                                label={o.label}
                                onClick={() => toggleSpecialCondition(o.v)}
                            />
                        ))}
                    </div>
                </Card>

                <Card title="관심 분야">
                    <p className="mb-3 text-sm text-gray-500">필요한 분야를 선택하세요</p>
                    <div className="flex flex-wrap gap-2">
                        {NEED_OPTIONS.map((o) => (
                            <MultiSelectChip
                                key={o.v}
                                active={form.needs?.includes(o.v) ?? false}
                                label={o.label}
                                onClick={() => toggleNeed(o.v)}
                            />
                        ))}
                    </div>
                </Card>
            </div>

            {/* 이메일 알림 설정 */}
            <div className="rounded-2xl bg-blue-50 p-6">
                <h2 className="text-lg font-bold text-[#0b2f6d] mb-4">📬 정책 알림 설정</h2>
                <div className="space-y-4">
                    <label className="flex items-start gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={form.emailNotificationEnabled ?? false}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    emailNotificationEnabled: e.target.checked,
                                })
                            }
                            className="mt-1 h-5 w-5 rounded border-gray-300"
                        />
                        <div>
                            <span className="font-semibold">정책정보 알림 수신 동의</span>
                            <p className="text-sm text-gray-600 mt-1">
                                새로운 정책이 등록되면 회원님의 프로필과 매칭되는 정책을 이메일로 알려드립니다.
                            </p>
                        </div>
                    </label>

                    {form.emailNotificationEnabled && (
                        <div className="ml-8">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                알림 받을 이메일 주소
                            </label>
                            <input
                                type="email"
                                value={form.notificationEmail ?? ""}
                                onChange={(e) =>
                                    setForm({
                                        ...form,
                                        notificationEmail: e.target.value || null,
                                    })
                                }
                                placeholder="example@email.com"
                                className="h-11 w-full max-w-md rounded-lg border px-3 text-sm outline-none focus:border-blue-800"
                            />
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-end">
                <Link href="/mypage" className="text-sm text-gray-600 hover:underline">
                    마이페이지로 돌아가기
                </Link>
            </div>
        </div>
    );
}
