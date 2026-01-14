// features/calendar/CalendarPageClient.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchCalendarEvents } from "./calendar.api";
import { CalendarEvent, CalendarPeriodMode } from "./calendar.types";
import { expandDateKeysInclusive, toDateKey } from "./calendar.utils";

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
    const last = endOfMonth(baseMonth);

    const firstDow = first.getDay(); // 0=Sun
    const gridStart = new Date(first);
    gridStart.setDate(first.getDate() - firstDow);

    // 6주(42칸) 고정: 대부분의 달력 UI가 안정적으로 보임
    const days: Date[] = [];
    const cur = new Date(gridStart);
    for (let i = 0; i < 42; i++) {
        days.push(new Date(cur));
        cur.setDate(cur.getDate() + 1);
    }

    // last는 실제 계산엔 필요 없지만, 참고용으로 남김
    void last;
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

    useEffect(() => {
        let alive = true;
        (async () => {
            setLoading(true);
            try {
                const list = await fetchCalendarEvents(mode);
                if (alive) setEvents(list);
            } finally {
                if (alive) setLoading(false);
            }
        })();
        return () => {
            alive = false;
        };
    }, [mode]);

    // ✅ 날짜(YYYY-MM-DD) -> 이벤트들 매핑
    const eventsByDate = useMemo(() => {
        const map = new Map<string, CalendarEvent[]>();

        for (const ev of events) {
            const keys = expandDateKeysInclusive(ev.start, ev.end);
            for (const k of keys) {
                const arr = map.get(k) ?? [];
                arr.push(ev);
                map.set(k, arr);
            }
        }

        // 같은 날짜에 여러 이벤트가 있으면 제목 기준 정렬(원하면 바꿔도 됨)
        for (const [k, arr] of map) {
            arr.sort((a, b) => a.title.localeCompare(b.title, "ko"));
            map.set(k, arr);
        }

        return map;
    }, [events]);

    const gridDays = useMemo(() => buildMonthGrid(month), [month]);
    const monthLabel = useMemo(() => {
        const y = month.getFullYear();
        const m = String(month.getMonth() + 1).padStart(2, "0");
        return `${y}.${m}`;
    }, [month]);

    const monthStart = startOfMonth(month);
    const monthEnd = endOfMonth(month);

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* ✅ 상단 필터 바*/}
            <section className="mb-6">
                <div className="flex items-center gap-2 rounded-xl border bg-white p-3">
                    <input
                        className="h-9 flex-1 rounded-lg border px-3 text-sm outline-none"
                        placeholder="정책명, 키워드로 검색하세요. (UI 목업)"
                        onKeyDown={(e) => {
                            // TODO: 실제 검색 로직은 다음 단계에서
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
            <section className="rounded-xl border bg-white">
                {/* 요일 헤더 */}
                <div className="grid grid-cols-7 border-b text-center text-xs font-semibold text-gray-600">
                    {["SUN", "MON", "TUE", "WED", "THR", "FRI", "SAT"].map((w) => (
                        <div key={w} className="py-2">
                            {w}
                        </div>
                    ))}
                </div>

                {/* 날짜 그리드 */}
                <div className="grid grid-cols-7">
                    {gridDays.map((d) => {
                        const inMonth = d >= monthStart && d <= monthEnd;
                        const k = toDateKey(d);
                        const dayEvents = eventsByDate.get(k) ?? [];

                        return (
                            <div
                                key={k}
                                className={`min-h-[120px] border-b border-r p-2 ${inMonth ? "bg-white" : "bg-gray-50"
                                    }`}
                            >
                                <div className="mb-2 flex items-center justify-between">
                                    <span className={`text-xs ${inMonth ? "text-gray-900" : "text-gray-400"}`}>
                                        {d.getDate()}
                                    </span>
                                </div>

                                {/* ✅ 이벤트 렌더 (너무 많으면 3개만 보여주고 +n) */}
                                <div className="space-y-1">
                                    {dayEvents.slice(0, 3).map((ev) => (
                                        <button
                                            key={`${ev.id}-${ev.mode}`}
                                            type="button"
                                            className="w-full truncate rounded bg-gray-100 px-2 py-1 text-left text-[11px] text-gray-800 hover:bg-gray-200"
                                            onClick={() => router.push(`/policy/${ev.id}`)}
                                            title={ev.title}
                                        >
                                            {ev.title}
                                        </button>
                                    ))}

                                    {dayEvents.length > 3 && (
                                        <div className="text-[11px] text-gray-500">+{dayEvents.length - 3} more</div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </section>
        </div>
    );
}
