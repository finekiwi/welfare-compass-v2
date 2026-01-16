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

    // ✅ Hover 상태
    const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);

    // ✅ 모달 상태
    const [modalDateKey, setModalDateKey] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;
        (async () => {
            setLoading(true);
            try {
                const list = await fetchCalendarEvents(
                    mode,
                    month.getFullYear(),
                    month.getMonth() + 1
                );
                if (alive) setEvents(list);
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

    // ✅ A안: 주 단위 Segment 계산
    const weekSegments = useMemo(() => {
        const segments = buildWeekSegments(events, gridDays);
        return assignAllLanes(segments);
    }, [events, gridDays]);

    // ✅ Overflow 계산
    const overflowMap = useMemo(() => {
        return calculateOverflow(weekSegments, gridDays);
    }, [weekSegments, gridDays]);

    // ✅ 이벤트 ID → 이벤트 맵
    const eventMap = useMemo(() => {
        const map = new Map<string, CalendarEvent>();
        for (const ev of events) {
            map.set(ev.id, ev);
        }
        return map;
    }, [events]);

    // ✅ 특정 날짜의 모든 이벤트 (모달용)
    const getEventsForDate = useCallback((dateKey: string): CalendarEvent[] => {
        const result: CalendarEvent[] = [];
        for (const ev of events) {
            const evStart = toDateKey(ev.start);
            const evEnd = toDateKey(ev.end);
            if (dateKey >= evStart && dateKey <= evEnd) {
                result.push(ev);
            }
        }
        return result;
    }, [events]);

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

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* ✅ 상단 필터 바 */}
            <section className="mb-6">
                <div className="flex items-center gap-2 rounded-xl border bg-white p-3">
                    <input
                        className="h-9 flex-1 rounded-lg border px-3 text-sm outline-none"
                        placeholder="정책명, 키워드로 검색하세요."
                        onKeyDown={(e) => {
                            if (e.key === "Enter") console.log("search");
                        }}
                    />

                    {/* ✅ 기간 기준 토글 */}
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            className={`h-9 rounded-lg border px-3 text-xs ${mode === "apply" ? "bg-gray-900 text-white" : "bg-white text-gray-700"
                                }`}
                            onClick={() => setMode("apply")}
                        >
                            신청기간
                        </button>
                        <button
                            type="button"
                            className={`h-9 rounded-lg border px-3 text-xs ${mode === "biz" ? "bg-gray-900 text-white" : "bg-white text-gray-700"
                                }`}
                            onClick={() => setMode("biz")}
                        >
                            사업기간
                        </button>
                    </div>
                </div>

                <div className="mt-2 text-right text-[11px] text-gray-500">
                    {loading
                        ? "일정을 불러오는 중..."
                        : `표시 기준: ${mode === "apply" ? "신청기간" : "사업기간"} · 총 ${events.length}개 정책`}
                </div>
            </section>

            {/* ✅ 월 이동 헤더 */}
            <section className="mb-3 flex items-center justify-center gap-4">
                <button
                    type="button"
                    className="rounded-lg border px-3 py-2 text-sm"
                    onClick={() => setMonth((prev) => addMonths(prev, -1))}
                >
                    ◀
                </button>
                <div className="text-lg font-semibold">{monthLabel}</div>
                <button
                    type="button"
                    className="rounded-lg border px-3 py-2 text-sm"
                    onClick={() => setMonth((prev) => addMonths(prev, 1))}
                >
                    ▶
                </button>
            </section>

            {/* ✅ 달력 본문 */}
            <section className="rounded-xl border bg-white overflow-hidden">
                {/* 요일 헤더 */}
                <div className="grid grid-cols-7 border-b text-center text-xs font-semibold text-gray-600">
                    {["SUN", "MON", "TUE", "WED", "THR", "FRI", "SAT"].map((w) => (
                        <div key={w} className="py-2">
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

                            return (
                                <div
                                    key={k}
                                    className={`h-[145px] border-b border-r p-2 ${inMonth ? "bg-white" : "bg-gray-50"
                                        }`}
                                >
                                    <div className="flex items-center justify-between">
                                        <span
                                            className={`text-xs ${isToday
                                                ? "bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center"
                                                : inMonth
                                                    ? "text-gray-900"
                                                    : "text-gray-400"
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
