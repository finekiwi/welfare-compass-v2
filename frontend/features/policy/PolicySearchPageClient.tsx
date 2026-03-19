// features/policy/PolicySearchPageClient.tsx
"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { fetchPolicies } from "./policy.api";
import { Policy, PolicyCategory } from "./policy.types";
import { PolicyCard } from "./PolicyCard";
import { Pagination } from "@/components/common/Pagination";
import {
    CATEGORY_OPTIONS,
    SUBCATEGORY_OPTIONS,
    EMPLOYMENT_OPTIONS,
    EDUCATION_OPTIONS,
    MARRIAGE_OPTIONS,
    APPLY_STATUS_OPTIONS,
    SPECIAL_CONDITIONS,
} from "./policy.filters";

// ─── 컴포넌트 ──────────────────────────────────────────────────────

export function PolicySearchPageClient() {
    const pathname = usePathname();
    const searchParams = useSearchParams();

    // URL 파라미터로 초기 상태 설정
    const initialQ = searchParams.get("q") || "";
    const initialCategory = (searchParams.get("category") as PolicyCategory | "all") || "all";
    const initialApplyStatus = searchParams.get("apply_status") || "";
    const initialRegion = searchParams.get("region") || "";
    const initialSubcategory = searchParams.get("subcategory") || "";
    const initialEmploymentStatus = searchParams.get("employment_status") || "";
    const initialEducationStatus = searchParams.get("education_status") || "";
    const initialMarriageStatus = searchParams.get("marriage_status") || "";
    const initialAge = searchParams.get("age") || "";
    const initialOrdering = searchParams.get("ordering") || "";
    const initialSpecialConditions = {
        is_for_single_parent: searchParams.get("is_for_single_parent") === "true",
        is_for_disabled: searchParams.get("is_for_disabled") === "true",
        is_for_low_income: searchParams.get("is_for_low_income") === "true",
        is_for_newlywed: searchParams.get("is_for_newlywed") === "true",
    };
    const initialPage = Math.max(1, Number(searchParams.get("page") || "1"));

    // 기본 필터
    const [q, setQ] = useState(initialQ);
    const [category, setCategory] = useState<PolicyCategory | "all">(initialCategory);
    const [region, setRegion] = useState(initialRegion);

    // 고급 필터
    const [subcategory, setSubcategory] = useState(initialSubcategory);
    const [employmentStatus, setEmploymentStatus] = useState(initialEmploymentStatus);
    const [educationStatus, setEducationStatus] = useState(initialEducationStatus);
    const [marriageStatus, setMarriageStatus] = useState(initialMarriageStatus);
    const [age, setAge] = useState<string>(initialAge);
    const [specialConditions, setSpecialConditions] = useState(initialSpecialConditions);
    const [applyStatus, setApplyStatus] = useState(initialApplyStatus);

    // 페이지네이션
    const [page, setPage] = useState(initialPage);
    const [pageSize, setPageSize] = useState(12);
    const [items, setItems] = useState<Policy[]>([]);
    const [totalCount, setTotalCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [ordering, setOrdering] = useState(initialOrdering);
    const didInitPageResetRef = useRef(false);
    const didInitUrlSyncRef = useRef(false);

    // 뷰 모드
    const [viewMode, setViewMode] = useState<"grid" | "list">("grid");


    // ???? ????(popstate)? ??? ? URL page? ??? ??
    useEffect(() => {
        const syncPageFromUrl = () => {
            const url = new URL(window.location.href);
            const nextPage = Math.max(1, Number(url.searchParams.get("page") || "1"));
            setPage((prev) => (prev === nextPage ? prev : nextPage));
        };

        syncPageFromUrl();
        window.addEventListener("popstate", syncPageFromUrl);
        return () => window.removeEventListener("popstate", syncPageFromUrl);
    }, []);


    // 초기 마운트 시 로컬 스토리지에서 뷰 모드 복원
    useEffect(() => {
        const savedMode = localStorage.getItem("policyViewMode");
        if (savedMode === "grid" || savedMode === "list") {
            setViewMode(savedMode);
        }
    }, []);

    const handleViewModeChange = (mode: "grid" | "list") => {
        setViewMode(mode);
        localStorage.setItem("policyViewMode", mode);
    };

    // 필터 패널 토글 (초기 고급 필터가 있으면 열어둠)
    const [showFilters, setShowFilters] = useState(
        !!(
            initialApplyStatus ||
            initialSubcategory ||
            initialEmploymentStatus ||
            initialEducationStatus ||
            initialMarriageStatus ||
            initialAge ||
            initialSpecialConditions.is_for_single_parent ||
            initialSpecialConditions.is_for_disabled ||
            initialSpecialConditions.is_for_low_income ||
            initialSpecialConditions.is_for_newlywed
        ),
    );

    // 활성 필터 개수 산출
    const activeFilterCount = useMemo(() => {
        let count = 0;
        if (subcategory) count++;
        if (employmentStatus) count++;
        if (educationStatus) count++;
        if (marriageStatus) count++;
        if (age) count++;
        if (applyStatus) count++;
        if (specialConditions.is_for_single_parent) count++;
        if (specialConditions.is_for_disabled) count++;
        if (specialConditions.is_for_low_income) count++;
        if (specialConditions.is_for_newlywed) count++;
        return count;
    }, [subcategory, employmentStatus, educationStatus, marriageStatus, age, applyStatus, specialConditions]);

    // 활성 필터 칩(Chip) 데이터 생성
    const activeFilterChips = useMemo(() => {
        const chips: { id: string; label: string; onRemove: () => void }[] = [];

        if (subcategory) {
            const opt = SUBCATEGORY_OPTIONS.find(o => o.value === subcategory);
            chips.push({ id: 'subcategory', label: opt?.label || subcategory, onRemove: () => setSubcategory("") });
        }
        if (employmentStatus) {
            const opt = EMPLOYMENT_OPTIONS.find(o => o.value === employmentStatus);
            chips.push({ id: 'employmentStatus', label: opt?.label || employmentStatus, onRemove: () => setEmploymentStatus("") });
        }
        if (educationStatus) {
            const opt = EDUCATION_OPTIONS.find(o => o.value === educationStatus);
            chips.push({ id: 'educationStatus', label: opt?.label || educationStatus, onRemove: () => setEducationStatus("") });
        }
        if (marriageStatus) {
            const opt = MARRIAGE_OPTIONS.find(o => o.value === marriageStatus);
            chips.push({ id: 'marriageStatus', label: opt?.label || marriageStatus, onRemove: () => setMarriageStatus("") });
        }
        if (age) {
            chips.push({ id: 'age', label: `만 ${age}세`, onRemove: () => setAge("") });
        }
        if (applyStatus) {
            const opt = APPLY_STATUS_OPTIONS.find(o => o.value === applyStatus);
            chips.push({ id: 'applyStatus', label: opt?.label || applyStatus, onRemove: () => setApplyStatus("") });
        }
        
        SPECIAL_CONDITIONS.forEach(({ key, label }) => {
            if (specialConditions[key as keyof typeof specialConditions]) {
                chips.push({
                    id: `special_${key}`,
                    label,
                    onRemove: () => setSpecialConditions(prev => ({ ...prev, [key]: false }))
                });
            }
        });

        return chips;
    }, [subcategory, employmentStatus, educationStatus, marriageStatus, age, applyStatus, specialConditions]);

    // 필터 초기화
    const resetFilters = useCallback(() => {
        setSubcategory("");
        setEmploymentStatus("");
        setEducationStatus("");
        setMarriageStatus("");
        setAge("");
        setApplyStatus("");
        setSpecialConditions({
            is_for_single_parent: false,
            is_for_disabled: false,
            is_for_low_income: false,
            is_for_newlywed: false,
        });
    }, []);

    // 검색 조건 변경 시 1페이지로 리셋
    useEffect(() => {
        if (!didInitPageResetRef.current) {
            didInitPageResetRef.current = true;
            return;
        }
        setPage(1);
    }, [q, category, region, pageSize, subcategory, employmentStatus, educationStatus, marriageStatus, age, applyStatus, specialConditions, ordering]);

    // 데이터 로드
    useEffect(() => {
        let alive = true;

        (async () => {
            setLoading(true);
            try {
                const { policies, totalCount } = await fetchPolicies({
                    q,
                    category,
                    region,
                    page,
                    page_size: pageSize,
                    subcategory: subcategory || undefined,
                    employment_status: employmentStatus || undefined,
                    education_status: educationStatus || undefined,
                    marriage_status: marriageStatus || undefined,
                    age: age ? Number(age) : undefined,
                    is_for_single_parent: specialConditions.is_for_single_parent || undefined,
                    is_for_disabled: specialConditions.is_for_disabled || undefined,
                    is_for_low_income: specialConditions.is_for_low_income || undefined,
                    is_for_newlywed: specialConditions.is_for_newlywed || undefined,
                    apply_status: applyStatus || undefined,
                    ordering: ordering || undefined,
                });
                if (alive) {
                    setItems(policies);
                    setTotalCount(totalCount);
                }
            } finally {
                if (alive) setLoading(false);
            }
        })();

        return () => { alive = false; };
    }, [q, category, region, page, pageSize, subcategory, employmentStatus, educationStatus, marriageStatus, age, applyStatus, specialConditions, ordering]);

    // URL 쿼리에 현재 검색/페이지 상태 동기화 (뒤로가기 시 복원)
    useEffect(() => {
        if (typeof window === "undefined") return;
        // 첫 마운트는 건너뜀: 뒤로가기 시 stale state가 URL을 덮어쓰는 것 방지
        if (!didInitUrlSyncRef.current) {
            didInitUrlSyncRef.current = true;
            return;
        }
        const params = new URLSearchParams(window.location.search);

        const setOrDelete = (key: string, value: string) => {
            if (value) params.set(key, value);
            else params.delete(key);
        };

        setOrDelete("q", q.trim());
        setOrDelete("category", category === "all" ? "" : category);
        setOrDelete("region", region);
        setOrDelete("subcategory", subcategory);
        setOrDelete("employment_status", employmentStatus);
        setOrDelete("education_status", educationStatus);
        setOrDelete("marriage_status", marriageStatus);
        setOrDelete("age", age);
        setOrDelete("apply_status", applyStatus);
        setOrDelete("ordering", ordering);
        setOrDelete("is_for_single_parent", specialConditions.is_for_single_parent ? "true" : "");
        setOrDelete("is_for_disabled", specialConditions.is_for_disabled ? "true" : "");
        setOrDelete("is_for_low_income", specialConditions.is_for_low_income ? "true" : "");
        setOrDelete("is_for_newlywed", specialConditions.is_for_newlywed ? "true" : "");
        if (page > 1) params.set("page", String(page));
        else params.delete("page");

        const next = `${pathname}${params.toString() ? `?${params.toString()}` : ""}`;
        const current = `${pathname}${window.location.search}`;
        if (next !== current) {
            window.history.replaceState(null, "", next);
        }
    }, [
        pathname,
        q,
        category,
        region,
        subcategory,
        employmentStatus,
        educationStatus,
        marriageStatus,
        age,
        applyStatus,
        ordering,
        specialConditions,
        page,
    ]);

    const countText = useMemo(() => {
        if (loading) return "불러오는 중...";
        return `총 ${totalCount}건`;
    }, [totalCount, loading]);

    // ─── 공통 select 스타일 ────────────────────────────────────────
    const selectClass =
        "h-9 rounded-lg border border-gray-200 bg-white px-3 text-xs text-gray-700 outline-none transition-colors hover:border-gray-300 focus:border-gray-500";

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* ─── 1행: 검색 바 ──────────────────────────────────── */}
            <section className="mb-6">
                <div className="flex w-full items-center gap-2 rounded-xl border border-gray-200 bg-white p-3">
                    {/* region */}
                    <select
                        className={selectClass}
                        value={region}
                        onChange={(e) => setRegion(e.target.value)}
                    >
                        <option value="">전체 지역</option>
                        <option value="서울시">서울시</option>
                        <option value="전국">전국</option>
                    </select>

                    {/* category */}
                    <select
                        className={selectClass}
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
                        className="h-9 flex-1 rounded-lg border border-gray-200 px-3 text-xs outline-none transition-colors hover:border-gray-300 focus:border-gray-500"
                        placeholder="정책명 또는 키워드를 입력하세요"
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                    />

                    <button
                        type="button"
                        className="h-9 rounded-lg bg-gray-600 px-5 text-xs font-medium text-white transition-colors hover:bg-gray-700 active:bg-gray-800"
                        onClick={() => setPage(1)}
                    >
                        검색
                    </button>
                </div>

                {/* ─── 필터 토글 + 페이지 사이즈 + 결과 건수 ──── */}
                <div className="mt-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${showFilters
                                ? "border-gray-500 bg-gray-50 text-gray-700"
                                : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
                                }`}
                            onClick={() => setShowFilters((v) => !v)}
                        >
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                            </svg>
                            상세 필터
                            {activeFilterCount > 0 && (
                                <span className="flex h-4 min-w-[16px] items-center justify-center rounded-full bg-blue-600 px-1 text-[10px] font-bold text-white">
                                    {activeFilterCount}
                                </span>
                            )}
                            <svg
                                className={`h-3 w-3 transition-transform ${showFilters ? "rotate-180" : ""}`}
                                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>

                        <select
                            className="h-8 rounded-lg border border-gray-200 px-2 text-[11px] text-gray-600 outline-none"
                            value={ordering}
                            onChange={(e) => setOrdering(e.target.value)}
                        >
                            <option value="">마감임박순</option>
                            <option value="-created_at">최신등록순</option>
                            <option value="created_at">과거등록순</option>
                        </select>

                        <select
                            className="h-8 rounded-lg border border-gray-200 px-2 text-[11px] text-gray-600 outline-none"
                            value={pageSize}
                            onChange={(e) => setPageSize(Number(e.target.value))}
                        >
                            <option value={8}>8개씩</option>
                            <option value={12}>12개씩</option>
                            <option value={16}>16개씩</option>
                            <option value={24}>24개씩</option>
                        </select>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="text-[11px] text-gray-500 mr-2">{countText}</div>

                        {/* 뷰 모드 토글 */}
                        <div className="flex bg-gray-100 p-0.5 rounded-lg border border-gray-200">
                            <button
                                type="button"
                                className={`px-2 py-1 flex items-center justify-center rounded-md text-xs font-medium transition-colors ${viewMode === "grid" ? "bg-white text-gray-800 shadow-sm" : "text-gray-400 hover:text-gray-600"}`}
                                onClick={() => handleViewModeChange("grid")}
                                title="그리드 보기"
                            >
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
                            </button>
                            <button
                                type="button"
                                className={`px-2 py-1 flex items-center justify-center rounded-md text-xs font-medium transition-colors ${viewMode === "list" ? "bg-white text-gray-800 shadow-sm" : "text-gray-400 hover:text-gray-600"}`}
                                onClick={() => handleViewModeChange("list")}
                                title="리스트 보기"
                            >
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
                            </button>
                        </div>
                    </div>
                </div>

                {/* ─── 접이식 고급 필터 패널 ────────────────────── */}
                {showFilters && (
                    <div className="mt-3 animate-in slide-in-from-top-2 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                        <div className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-3 lg:grid-cols-4">
                            {/* 세부분류 */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">세부분류</label>
                                <select className={selectClass} value={subcategory} onChange={(e) => setSubcategory(e.target.value)}>
                                    {SUBCATEGORY_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 취업상태 */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">취업상태</label>
                                <select className={selectClass} value={employmentStatus} onChange={(e) => setEmploymentStatus(e.target.value)}>
                                    {EMPLOYMENT_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 학력 */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">학력</label>
                                <select className={selectClass} value={educationStatus} onChange={(e) => setEducationStatus(e.target.value)}>
                                    {EDUCATION_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 혼인상태 */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">혼인상태</label>
                                <select className={selectClass} value={marriageStatus} onChange={(e) => setMarriageStatus(e.target.value)}>
                                    {MARRIAGE_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 나이 */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">나이</label>
                                <input
                                    type="number"
                                    className="h-9 rounded-lg border border-gray-200 px-3 text-xs outline-none transition-colors hover:border-gray-300 focus:border-gray-500"
                                    placeholder="만 나이 입력"
                                    value={age}
                                    min={0}
                                    max={100}
                                    onChange={(e) => setAge(e.target.value)}
                                />
                            </div>

                            {/* 신청상태 */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">신청상태</label>
                                <select className={selectClass} value={applyStatus} onChange={(e) => setApplyStatus(e.target.value)}>
                                    {APPLY_STATUS_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 특수조건 (체크박스) - 2칸 차지 */}
                            <div className="col-span-2 flex flex-col gap-1.5">
                                <label className="text-[11px] font-semibold text-gray-500">특수조건</label>
                                <div className="flex flex-wrap gap-2">
                                    {SPECIAL_CONDITIONS.map(({ key, label }) => (
                                        <label
                                            key={key}
                                            className={`flex cursor-pointer items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors ${specialConditions[key]
                                                ? "border-gray-500 bg-gray-50 text-gray-700"
                                                : "border-gray-200 bg-gray-50 text-gray-600 hover:border-gray-300"
                                                }`}
                                        >
                                            <input
                                                type="checkbox"
                                                className="sr-only"
                                                checked={specialConditions[key]}
                                                onChange={(e) =>
                                                    setSpecialConditions((prev) => ({
                                                        ...prev,
                                                        [key]: e.target.checked,
                                                    }))
                                                }
                                            />
                                            <span className={`flex h-3.5 w-3.5 items-center justify-center rounded border text-[9px] ${specialConditions[key]
                                                ? "border-blue-500 bg-blue-500 text-white"
                                                : "border-gray-300 bg-white"
                                                }`}>
                                                {specialConditions[key] && "✓"}
                                            </span>
                                            {label}
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* 활성 필터 칩 및 초기화 버튼 */}
                        <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between border-t border-gray-100 pt-3 gap-3">
                            <div className="flex flex-wrap items-center gap-1.5 flex-1 p-0.5">
                                {activeFilterChips.map((chip) => (
                                    <span
                                        key={chip.id}
                                        className="flex items-center gap-1 rounded-md bg-blue-50 pl-2 pr-1 py-1 text-[11px] font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10"
                                    >
                                        {chip.label}
                                        <button
                                            type="button"
                                            className="ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-blue-500 transition-colors hover:bg-blue-100 hover:text-blue-900 focus:outline-none"
                                            onClick={chip.onRemove}
                                            aria-label={`${chip.label} 필터 해제`}
                                        >
                                            ✕
                                        </button>
                                    </span>
                                ))}
                            </div>
                            <button
                                type="button"
                                className="shrink-0 self-end sm:self-auto rounded-lg border border-gray-200 px-4 py-1.5 text-xs text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40"
                                onClick={resetFilters}
                                disabled={activeFilterCount === 0}
                            >
                                전체 필터 초기화
                            </button>
                        </div>
                    </div>
                )}
            </section>

            {/* ─── 카드 리스트 ──────────────────────────────────── */}
            <section className="w-full">
                <div className={viewMode === "grid" ? "grid grid-cols-2 gap-4 md:grid-cols-4" : "flex flex-col gap-4"}>
                    {items.map((p) => (
                        <PolicyCard key={p.id} policy={p} viewMode={viewMode} />
                    ))}
                </div>

                {!loading && items.length === 0 && (
                    <div className="mt-10 text-center text-sm text-gray-500">
                        조건에 맞는 정책이 없습니다.
                    </div>
                )}
            </section>

            {/* ─── 페이지네이션 ─────────────────────────────────── */}
            <Pagination
                currentPage={page}
                totalCount={totalCount}
                itemsPerPage={pageSize}
                onPageChange={setPage}
            />
        </div>
    );
}
