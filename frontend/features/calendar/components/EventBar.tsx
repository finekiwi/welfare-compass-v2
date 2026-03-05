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

    // 위치 계산 (달력 셀 날짜(상단 30px 가량) 아래부터 시작하도록 top 시작점 조정)
    const left = `calc(${segment.startCol} * (100% / 7) + 2px)`;
    const width = `calc(${segment.endCol - segment.startCol + 1} * (100% / 7) - 4px)`;
    const top = `calc(${segment.lane} * 22px + 30px)`;

    return (
        <button
            type="button"
            className={`
                absolute h-[22px] flex items-center text-left text-[13px] cursor-pointer
                transition-all duration-150 ease-out rounded-md overflow-hidden
                ${isHovered ? "z-20 bg-gray-100/80" : "z-10"}
            `}
            style={{
                left,
                width,
                top,
                border: `1px dashed ${colors.borderColor}`,
                backgroundColor: colors.bgColor,
            }}
            onMouseEnter={() => onHover(segment.eventId)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onClick(segment.eventId)}
            title={segment.title}
        >
            {/* 카테고리 뱃지 (시작 주에서만 표시) */}
            {segment.isStart && (
                <span
                    className={`
                        flex-shrink-0 px-1.5 py-0.5 rounded flex items-center ml-0.5
                        text-[9px] font-bold
                        ${colors.badge} ${colors.badgeText}
                    `}
                >
                    {colors.label}
                </span>
            )}
            {/* 이벤트 제목 */}
            <span className="truncate px-1 text-gray-900">
                {segment.title}
            </span>
        </button>
    );
}
