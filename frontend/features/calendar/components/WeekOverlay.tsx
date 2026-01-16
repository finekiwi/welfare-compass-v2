// features/calendar/components/WeekOverlay.tsx
"use client";

import { WeekSegment, DayOverflow } from "../calendar.types";
import { EventBar } from "./EventBar";
import { OverflowButton } from "./OverflowButton";

interface WeekOverlayProps {
    weekIndex: number;
    segments: WeekSegment[];
    overflowMap: Map<string, DayOverflow>;
    gridDays: Date[];
    hoveredEventId: string | null;
    onHover: (eventId: string | null) => void;
    onEventClick: (eventId: string) => void;
    onOverflowClick: (dateKey: string) => void;
}

export function WeekOverlay({
    weekIndex,
    segments,
    overflowMap,
    gridDays,
    hoveredEventId,
    onHover,
    onEventClick,
    onOverflowClick,
}: WeekOverlayProps) {
    // lane이 -1이 아닌 segment만 렌더링
    const visibleSegments = segments.filter(s => s.lane >= 0);

    // 이 주의 overflow 버튼들
    const weekStartIdx = weekIndex * 7;
    const overflowButtons: { col: number; dateKey: string; count: number }[] = [];

    for (let col = 0; col < 7; col++) {
        const dayIndex = weekStartIdx + col;
        if (dayIndex >= gridDays.length) continue;

        const dateKey = toDateKey(gridDays[dayIndex]);
        const overflow = overflowMap.get(dateKey);

        if (overflow && overflow.count > 0) {
            overflowButtons.push({ col, dateKey, count: overflow.count });
        }
    }

    return (
        <div
            className="absolute left-0 right-0 pointer-events-none"
            style={{
                top: `calc(${weekIndex} * 145px)`,
                height: "145px",
            }}
        >
            {/* 이벤트 바들 */}
            {visibleSegments.map((segment, idx) => (
                <div key={`${segment.eventId}-${idx}`} className="pointer-events-auto">
                    <EventBar
                        segment={segment}
                        hoveredEventId={hoveredEventId}
                        onHover={onHover}
                        onClick={onEventClick}
                    />
                </div>
            ))}

            {/* Overflow 버튼들 */}
            {overflowButtons.map(({ col, dateKey, count }) => (
                <div key={dateKey} className="pointer-events-auto">
                    <OverflowButton
                        col={col}
                        count={count}
                        onClick={() => onOverflowClick(dateKey)}
                    />
                </div>
            ))}
        </div>
    );
}

// 유틸 함수 (calendar.utils.ts에서 import할 수도 있음)
function toDateKey(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}
