// features/calendar/CalendarPageClient.tsx
"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchCalendarEvents } from "./calendar.api";
import { CalendarEvent, CalendarPeriodMode, WeekSegment, DayOverflow } from "./calendar.types";
import { toDateKey } from "./calendar.utils";
import { buildWeekSegments, assignAllLanes, calculateOverflow } from "./utils/segmentUtils";
import { WeekOverlay } from "./components/WeekOverlay";
import { EventModal } from "./components/EventModal";
import Image from "next/image";
import { useAuthStore } from "@/stores/auth.store";
import { fetchScraps } from "../mypage/mypage.api";

function startOfMonth(d: Date) {
    return new Date(d.getFullYear(), d.getMonth(), 1);
}
function endOfMonth(d: Date) {
    return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}
function addMonths(d: Date, n: number) {
    return new Date(d.getFullYear(), d.getMonth() + n, 1);
}

/**
 * 월간 달력 그리드(6주 * 7일) 생성:
 * - 첫 주 시작을 일요일 기준으로 맞춤
 */
function buildMonthGrid(baseMonth: Date): Date[] {
    const first = startOfMonth(baseMonth);

    const firstDow = first.getDay(); // 0=Sun
    const gridStart = new Date(first);
    gridStart.setDate(first.getDate() - firstDow);

    // 6주(42칸) 고정
    const days: Date[] = [];
    const cur = new Date(gridStart);
    for (let i = 0; i < 42; i++) {
        days.push(new Date(cur));
        cur.setDate(cur.getDate() + 1);
    }

    return days;
}

export function CalendarPageClient() {
    const router = useRouter();

    // ✅ 기본은 "신청기간"
    const [mode, setMode] = useState<CalendarPeriodMode>("apply");

    // ✅ 보여줄 달(기본: 오늘이 속한 달)
    const [month, setMonth] = useState<Date>(() => startOfMonth(new Date()));

    // ✅ 이벤트 데이터
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(false);

    // ✅ 커스텀 달력 선택기 상태
    const [isPickerOpen, setIsPickerOpen] = useState(false);

    // ✅ 북마크 연동 상태
    const { isAuthenticated } = useAuthStore();
    const [scrapedIds, setScrapedIds] = useState<Set<string>>(new Set());

    // ✅ 북마크(스크랩) 데이터 로드 (로그인 시)
    useEffect(() => {
        if (!isAuthenticated) {
            setScrapedIds(new Set());
            return;
        }

        let alive = true;
        fetchScraps().then((scraps) => {
            if (!alive) return;
            const ids = new Set(scraps.map((s) => s.plcy_no));
            setScrapedIds(ids);
        }).catch((err) => {
            console.error("Failed to load scraps for calendar:", err);
        });

        return () => { alive = false; };
    }, [isAuthenticated]);

    // ✅ 검색 필터 (클라이언트 사이드)
    const [searchInput, setSearchInput] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    // ✅ Hover 상태
    const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);

    // ✅ 모달 상태
    const [modalDateKey, setModalDateKey] = useState<string | null>(null);

    // ✅ 에러 상태
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;
        (async () => {
            setLoading(true);
            setError(null);
            try {
                const list = await fetchCalendarEvents(
                    mode,
                    month.getFullYear(),
                    month.getMonth() + 1
                );
                if (alive) setEvents(list);
            } catch (err) {
                if (alive) {
                    setError("일정을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
                    setEvents([]);
                }
            } finally {
                if (alive) setLoading(false);
            }
        })();
        return () => {
            alive = false;
        };
    }, [mode, month]);

    // ✅ 달력 그리드
    const gridDays = useMemo(() => buildMonthGrid(month), [month]);

    const monthLabel = useMemo(() => {
        const y = month.getFullYear();
        const m = String(month.getMonth() + 1).padStart(2, "0");
        return `${y}.${m}`;
    }, [month]);

    const monthStart = startOfMonth(month);
    const monthEnd = endOfMonth(month);

    // ✅ 필터 적용 (검색어 + 카테고리 + 북마크)
    const filteredEvents = useMemo(() => {
        let res = events;

        // 1. 검색어 필터
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            res = res.filter((ev) => ev.title.toLowerCase().includes(q));
        }

        // 2. 카테고리/북마크 필터
        if (selectedCategories.length > 0) {
            const isBookmarkSelected = selectedCategories.includes("bookmark");
            const activeCats = selectedCategories.filter(c => c !== "bookmark");

            res = res.filter((ev) => {
                // (A) 북마크 필터 확인
                if (isBookmarkSelected && !scrapedIds.has(ev.id)) {
                    return false; // 북마크 선택시, 북마크 안된 항목은 무조건 제외
                }

                // (B) 일반 카테고리 필터 확인 (선택된 일반 카테고리가 없는 경우 통과)
                if (activeCats.length === 0) {
                    return true;
                }

                const cats = (ev.category || "기타").split(",").map(s => s.trim());
                return activeCats.some(c =>
                    cats.includes(c) ||
                    (c === "복지·문화" && cats.includes("복지문화")) ||
                    (c === "참여·권리" && cats.includes("참여권리"))
                );
            });
        }
        return res;
    }, [events, searchQuery, selectedCategories, scrapedIds]);

    // ✅ A안: 주 단위 Segment 계산
    const weekSegments = useMemo(() => {
        const segments = buildWeekSegments(filteredEvents, gridDays);
        return assignAllLanes(segments);
    }, [filteredEvents, gridDays]);

    // ✅ Overflow 계산
    const overflowMap = useMemo(() => {
        return calculateOverflow(weekSegments, gridDays);
    }, [weekSegments, gridDays]);



    // ✅ 특정 날짜의 모든 이벤트 (모달용)
    const getEventsForDate = useCallback((dateKey: string): CalendarEvent[] => {
        const result: CalendarEvent[] = [];
        for (const ev of filteredEvents) {
            const evStart = toDateKey(ev.start);
            const evEnd = toDateKey(ev.end);
            if (dateKey >= evStart && dateKey <= evEnd) {
                result.push(ev);
            }
        }
        return result;
    }, [filteredEvents]);

    // ✅ 핸들러
    const handleEventClick = useCallback((eventId: string) => {
        router.push(`/policy/${eventId}`);
    }, [router]);

    const handleOverflowClick = useCallback((dateKey: string) => {
        setModalDateKey(dateKey);
    }, []);

    const handleCloseModal = useCallback(() => {
        setModalDateKey(null);
    }, []);

    const toggleCategory = (catId: string) => {
        setSelectedCategories(prev =>
            prev.includes(catId) ? prev.filter(c => c !== catId) : [...prev, catId]
        );
    };

    const SIDEBAR_CATEGORIES = [
        { id: "bookmark", label: "북마크", icon: "/icons/home/bookmark.png", fallbackIcon: "⭐" },
        { id: "일자리", label: "일자리", icon: "/icons/home/job.png", fallbackIcon: "💼" },
        { id: "주거", label: "주거", icon: "/icons/home/housing.png", fallbackIcon: "🏠" },
        { id: "교육", label: "교육", icon: "/icons/home/entrepreneurship.png", fallbackIcon: "💡" },
        { id: "복지·문화", label: "복지·문화", icon: "/icons/home/emotional-wellbeing.png", fallbackIcon: "🤲" },
        { id: "참여·권리", label: "참여·권리", icon: "/icons/home/participation.png", fallbackIcon: "🌱" },
    ];

    return (
        <div className="mx-auto w-full max-w-[1300px] px-4 py-8">
            {/* ✅ 상단 헤더 영역 - 비율에 관계없이 중앙 완벽 배치를 위해 flex 사용 */}
            <header className="mb-3 flex items-center justify-between relative h-[40px]">
                {/* 1. 왼쪽 영역: Today 버튼 */}
                <div className="flex-1 flex items-center justify-start pl-2">
                    <button
                        type="button"
                        onClick={() => setMonth(startOfMonth(new Date()))}
                        className="px-3 text-xs font-semibold text-gray-700 bg-white flex items-center justify-center transition-colors cursor-pointer"
                        style={{ height: "36px" }}
                    >
                        today
                    </button>
                </div>

                {/* 2. 중앙 영역: 월/년도 네비게이션 및 선택기 */}
                <div className="flex-none flex items-center justify-center gap-2 sm:gap-4 text-sm font-bold tracking-tight text-gray-900 z-50">
                    <button
                        type="button"
                        className="p-1 px-1 text-gray-500 hover:text-gray-800 transition-colors"
                        onClick={() => setMonth((prev) => addMonths(prev, -1))}
                    >
                        ◀
                    </button>
                    {/* 커스텀 month picker */}
                    <div className="relative min-w-[80px] sm:min-w-[100px] text-center flex justify-center items-center z-[100]">
                        <button
                            type="button"
                            className="text-base font-bold text-gray-900 hover:text-gray-600 transition-colors px-1 sm:px-2 py-1 rounded-md hover:bg-gray-100 cursor-pointer text-nowrap"
                            onClick={() => setIsPickerOpen(!isPickerOpen)}
                        >
                            {monthLabel}
                        </button>

                        {/* 달력 선택 드롭다운 팝업 - 이제 텍스트 부모가 정중앙에 있으므로 팝업도 무조건 정중앙에 배치됨 */}
                        {isPickerOpen && (
                            <>
                                <div
                                    className="absolute top-[120%] left-1/2 -translate-x-1/2 bg-white border border-gray-200 shadow-[0_4px_24px_rgba(0,0,0,0.1)] rounded-2xl p-5 w-[280px] z-[120]"
                                >
                                    {/* 연도 조절 (좌/우) */}
                                    <div className="flex justify-between items-center mb-4 pb-3">
                                        <button
                                            type="button"
                                            className="p-1.5 rounded-md text-gray-500 transition-colors cursor-pointer"
                                            onClick={() => setMonth(prev => new Date(prev.getFullYear() - 1, prev.getMonth(), 1))}
                                        >
                                            ◀
                                        </button>
                                        <span className="font-semibold text-lg cursor-default">{month.getFullYear()}년</span>
                                        <button
                                            type="button"
                                            className="p-1.5 rounded-md text-gray-500 transition-colors cursor-pointer"
                                            onClick={() => setMonth(prev => new Date(prev.getFullYear() + 1, prev.getMonth(), 1))}
                                        >
                                            ▶
                                        </button>
                                    </div>

                                    {/* 3x4 월 격자 */}
                                    <div className="grid grid-cols-3 gap-2">
                                        {Array.from({ length: 12 }, (_, i) => i).map((m) => {
                                            const isSelected = month.getMonth() === m;
                                            const isCurrentMonth = month.getMonth() === m && month.getFullYear() === new Date().getFullYear();
                                            return (
                                                <button
                                                    key={m}
                                                    type="button"
                                                    className={`py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${isSelected
                                                        ? "bg-gray-800 text-white hover:bg-gray-700"
                                                        : isCurrentMonth
                                                            ? "bg-blue-600 text-white hover:bg-blue-700"
                                                            : "text-gray-600 bg-gray-50 hover:bg-gray-200"
                                                        }`}
                                                    onClick={() => {
                                                        setMonth(new Date(month.getFullYear(), m, 1));
                                                        setIsPickerOpen(false);
                                                    }}
                                                >
                                                    {m + 1}월
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                                {/* 팝업 외부 클릭 레이어 */}
                                <div
                                    className="fixed inset-0 z-[90] cursor-default"
                                    onClick={() => setIsPickerOpen(false)}
                                />
                            </>
                        )}
                    </div>
                    <button
                        type="button"
                        className="p-1 px-1 text-gray-600 hover:text-gray-800 transition-colors"
                        onClick={() => setMonth((prev) => addMonths(prev, 1))}
                    >
                        ▶
                    </button>
                </div>

                {/* 우측 영역: 검색바 */}
                <div className="flex-1 flex items-center justify-end relative pr-0 sm:pr-2 md:pr-4">
                    {/* 검색바 (밑줄 스타일) */}
                    <div className="flex items-center border-b-1 border-gray-300 py-1 px-1 focus-within:border-gray-400 transition-colors w-[130px] sm:w-[180px] lg:w-[240px]">
                        <Image
                            src="/icons/home/search.png"
                            alt="검색"
                            width={15}
                            height={15}
                            className="mr-1 sm:mr-2 opacity-60"
                        />
                        <input
                            className="flex-1 bg-transparent text-xs sm:text-sm outline-none placeholder:text-gray-400 min-w-0"
                            placeholder="정책명, 키워드로 검색하세요."
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") setSearchQuery(searchInput);
                            }}
                        />
                        {searchQuery && (
                            <button
                                type="button"
                                className="text-xs text-gray-400 hover:text-gray-600 px-2"
                                onClick={() => { setSearchInput(""); setSearchQuery(""); }}
                            >
                                ✕
                            </button>
                        )}
                    </div>
                </div>
            </header>

            {/* ✅ 에러 표시 */}
            {error && (
                <div className="mb-4 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 mx-2">
                    <span>{error}</span>
                    <button
                        type="button"
                        className="rounded-md border border-red-600 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-100"
                        onClick={() => setMonth((prev) => new Date(prev))}
                    >
                        다시 시도
                    </button>
                </div>
            )}

            {/* ✅ 메인 레이아웃 (캘린더 + 우측 사이드바) */}
            <div className="flex gap-6 items-start">

                {/* 캘린더 본문 영역 */}
                <section className="flex-1 rounded-lg border border-gray-300 bg-white overflow-hidden">
                    {/* 요일 헤더 */}
                    <div className="grid grid-cols-7 border-b border-gray-300 text-center text-xs font-semibold text-gray-600 bg-gray-50">
                        {["SUN", "MON", "TUE", "WED", "THR", "FRI", "SAT"].map((w, i) => (
                            <div key={w} className={`py-2 ${i === 0 ? "text-red-600" : ""} ${i === 6 ? "text-blue-800" : ""}`}>
                                {w}
                            </div>
                        ))}
                    </div>

                    {/* 날짜 그리드 + 오버레이 컨테이너 */}
                    <div className="relative">
                        {/* Layer 1: 날짜 그리드 */}
                        <div className="grid grid-cols-7">
                            {gridDays.map((d, idx) => {
                                const inMonth = d >= monthStart && d <= monthEnd;
                                const k = toDateKey(d);
                                const isToday = toDateKey(new Date()) === k;
                                const isSunday = d.getDay() === 0;
                                const isSaturday = d.getDay() === 6;

                                return (
                                    <div
                                        key={k}
                                        className={`h-[145px] border-b border-r border-gray-200 p-1 transition-colors ${inMonth ? "bg-white" : "bg-gray-50/50"
                                            }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <span
                                                className={`text-[13px] font-medium w-6 h-6 flex items-center justify-center rounded-full ${isToday
                                                    ? "bg-gray-700 text-white"
                                                    : inMonth
                                                        ? (isSunday ? "text-red-600" : isSaturday ? "text-blue-800" : "text-gray-900")
                                                        : "text-gray-300"
                                                    }`}
                                            >
                                                {d.getDate()}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Layer 2: 주 단위 오버레이 */}
                        {weekSegments.map((segments, weekIndex) => (
                            <WeekOverlay
                                key={weekIndex}
                                weekIndex={weekIndex}
                                segments={segments}
                                overflowMap={overflowMap}
                                gridDays={gridDays}
                                hoveredEventId={hoveredEventId}
                                onHover={setHoveredEventId}
                                onEventClick={handleEventClick}
                                onOverflowClick={handleOverflowClick}
                            />
                        ))}
                    </div>
                </section>

                {/* ✅ 우측 사이드바 영역 */}
                <aside className="w-[100px] shrink-0 flex flex-col gap-6 pt-1">

                    <div className="flex flex-col gap-2">
                        <button
                            type="button"
                            className={`h-[42px] rounded-lg border flex items-center justify-center text-xs font-bold transition-colors ${mode === "apply"
                                ? "bg-[#4a4a4a] text-white border-[#4a4a4a]"
                                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                                }`}
                            onClick={() => setMode("apply")}
                        >
                            신청기간
                        </button>
                        <button
                            type="button"
                            className={`h-[42px] rounded-lg border flex items-center justify-center text-xs font-bold transition-colors ${mode === "biz"
                                ? "bg-[#4a4a4a] text-white border-[#4a4a4a]"
                                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                                }`}
                            onClick={() => setMode("biz")}
                        >
                            사업기간
                        </button>
                        <button
                            type="button"
                            className="h-[42px] mt-1 rounded-lg border flex items-center justify-center text-xs font-bold transition-colors bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
                            onClick={() => router.push("/policy?apply_status=always")}
                        >
                            상시모집 보기
                        </button>
                    </div>

                    {/* 카테고리 필터 그룹 (이미지와 동일한 수직 탭 메뉴형) */}
                    <div className="flex flex-col border border-gray-300 rounded-lg bg-white overflow-hidden">
                        {SIDEBAR_CATEGORIES.map((cat, idx) => {
                            const isSelected = selectedCategories.includes(cat.id);
                            const isLast = idx === SIDEBAR_CATEGORIES.length - 1;
                            return (
                                <button
                                    key={cat.id}
                                    type="button"
                                    onClick={() => toggleCategory(cat.id)}
                                    className={`flex flex-col items-center justify-center py-3 transition-colors ${!isLast ? "border-b border-gray-200" : ""
                                        } ${isSelected ? "bg-gray-100" : "hover:bg-gray-50"}`}
                                >
                                    <div className={`relative flex items-center justify-center opacity-90 ${cat.id === "bookmark" ? "w-8 h-8 mb-2" : "w-14 h-14"}`}>
                                        <Image
                                            src={cat.icon}
                                            alt={cat.label}
                                            fill
                                            className="object-contain transition-opacity duration-200"
                                            sizes="64px"
                                            quality={100}
                                            unoptimized
                                            onError={(e) => {
                                                e.currentTarget.style.display = 'none';
                                                const fallback = e.currentTarget.parentElement?.querySelector('.fallback-icon') as HTMLElement;
                                                if (fallback) fallback.style.display = 'block';
                                            }}
                                        />
                                        <span className="fallback-icon text-3xl hidden">{cat.fallbackIcon}</span>
                                    </div>
                                    <span className={`text-[12px] font-semibold ${isSelected ? "text-gray-900" : "text-gray-600"}`}>
                                        {cat.label}
                                    </span>
                                </button>
                            );
                        })}
                    </div>

                    {/* 하단 표시 기준 안내 텍스트 (옵션) */}
                    <div className="text-center text-[11px] text-gray-400 leading-tight">
                        {loading ? "불러오는 중..." : `총 ${filteredEvents.length}건`}
                    </div>
                </aside>

            </div>

            {/* ✅ Layer 3: 모달 */}
            {modalDateKey && (
                <EventModal
                    date={modalDateKey}
                    events={getEventsForDate(modalDateKey)}
                    onClose={handleCloseModal}
                    onEventClick={handleEventClick}
                />
            )}
        </div>
    );
}
