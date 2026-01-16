// features/calendar/components/EventModal.tsx
"use client";

import { CalendarEvent } from "../calendar.types";
import { getCategoryColor } from "../constants/categoryColors";

interface EventModalProps {
    date: string; // YYYY-MM-DD
    events: CalendarEvent[];
    onClose: () => void;
    onEventClick: (eventId: string) => void;
}

export function EventModal({ date, events, onClose, onEventClick }: EventModalProps) {
    // 날짜 포맷팅
    const d = new Date(date);
    const dateLabel = `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
            onClick={onClose}
        >
            <div
                className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* 헤더 */}
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-gray-900">{dateLabel}</h2>
                    <button
                        type="button"
                        className="text-gray-400 hover:text-gray-600"
                        onClick={onClose}
                    >
                        ✕
                    </button>
                </div>

                {/* 이벤트 목록 */}
                <div className="max-h-[400px] overflow-y-auto space-y-2">
                    {events.length === 0 ? (
                        <p className="text-sm text-gray-500">해당 날짜에 일정이 없습니다.</p>
                    ) : (
                        events.map((ev) => {
                            const colors = getCategoryColor(ev.category);
                            return (
                                <button
                                    key={ev.id}
                                    type="button"
                                    className={`
                    w-full text-left p-3 rounded-lg border
                    ${colors.bg} ${colors.text} ${colors.border}
                    hover:brightness-95 transition-all
                  `}
                                    onClick={() => onEventClick(ev.id)}
                                >
                                    <div className="font-medium text-sm truncate">{ev.title}</div>
                                    <div className="text-xs opacity-75 mt-1">
                                        {formatDateRange(ev.start, ev.end)}
                                    </div>
                                </button>
                            );
                        })
                    )}
                </div>

                {/* 닫기 버튼 */}
                <div className="mt-4 flex justify-end">
                    <button
                        type="button"
                        className="px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                        onClick={onClose}
                    >
                        닫기
                    </button>
                </div>
            </div>
        </div>
    );
}

function formatDateRange(start: Date, end: Date): string {
    const format = (d: Date) =>
        `${d.getMonth() + 1}/${d.getDate()}`;

    if (start.getTime() === end.getTime()) {
        return format(start);
    }
    return `${format(start)} ~ ${format(end)}`;
}
