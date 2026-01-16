// features/calendar/components/EventBar.tsx
"use client";

import { WeekSegment } from "../calendar.types";
import { getCategoryColor } from "../constants/categoryColors";

interface EventBarProps {
    segment: WeekSegment;
    onHover: (eventId: string | null) => void;
    hoveredEventId: string | null;
    onClick: (eventId: string) => void;
}

export function EventBar({ segment, onHover, hoveredEventId, onClick }: EventBarProps) {
    const colors = getCategoryColor(segment.category);
    const isHovered = hoveredEventId === segment.eventId;

    // 위치 계산 (CSS variables 사용)
    const left = `calc(${segment.startCol} * (100% / 7) + 2px)`;
    const width = `calc(${segment.endCol - segment.startCol + 1} * (100% / 7) - 4px)`;
    const top = `calc(${segment.lane} * 22px + 28px)`;

    // 라운딩 클래스
    const roundingClasses = [
        segment.isStart ? "rounded-l-sm" : "",
        segment.isEnd ? "rounded-r-sm" : "",
    ].join(" ");

    return (
        <button
            type="button"
            className={`
        absolute h-[18px] px-1 text-left text-[11px] truncate cursor-pointer
        transition-all duration-150 ease-out
        border
        ${colors.bg} ${colors.text} ${colors.border}
        ${isHovered ? "z-20 brightness-95" : "z-10"}
        ${roundingClasses}
      `}
            style={{
                left,
                width,
                top,
            }}
            onMouseEnter={() => onHover(segment.eventId)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onClick(segment.eventId)}
            title={segment.title}
        >
            {segment.title}
        </button>
    );
}
