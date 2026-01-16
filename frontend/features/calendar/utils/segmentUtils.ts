// features/calendar/utils/segmentUtils.ts
// 주 단위 Segment 분할 및 Lane 할당 알고리즘

import { CalendarEvent, WeekSegment, DayOverflow } from "../calendar.types";
import { toDateKey } from "../calendar.utils";

const MAX_LANES = 4; // 최대 4줄

/**
 * 날짜를 그리드 인덱스로 변환 (0~41)
 */
function findGridIndex(gridDays: Date[], targetDate: Date): number {
    const targetTime = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate()).getTime();

    for (let i = 0; i < gridDays.length; i++) {
        const gridTime = new Date(gridDays[i].getFullYear(), gridDays[i].getMonth(), gridDays[i].getDate()).getTime();
        if (gridTime === targetTime) return i;
    }

    // 범위 밖이면 가장 가까운 값 반환
    const firstTime = new Date(gridDays[0].getFullYear(), gridDays[0].getMonth(), gridDays[0].getDate()).getTime();
    const lastTime = new Date(gridDays[41].getFullYear(), gridDays[41].getMonth(), gridDays[41].getDate()).getTime();

    if (targetTime < firstTime) return 0;
    if (targetTime > lastTime) return 41;

    return -1;
}

/**
 * 이벤트 배열을 주 단위 Segment로 분할
 */
export function buildWeekSegments(
    events: CalendarEvent[],
    gridDays: Date[]
): WeekSegment[][] {
    // 6주 배열 초기화
    const weeks: WeekSegment[][] = [[], [], [], [], [], []];

    const gridStart = gridDays[0];
    const gridEnd = gridDays[41];

    for (const event of events) {
        // 1. 달력 범위와 이벤트 범위의 교집합 계산
        const visibleStart = event.start < gridStart ? gridStart : event.start;
        const visibleEnd = event.end > gridEnd ? gridEnd : event.end;

        if (visibleStart > visibleEnd) continue; // 범위 밖

        // 2. 시작/종료 날짜의 그리드 인덱스 찾기
        const startIdx = findGridIndex(gridDays, visibleStart);
        const endIdx = findGridIndex(gridDays, visibleEnd);

        if (startIdx === -1 || endIdx === -1) continue;

        // 3. 이벤트의 실제 시작/종료 인덱스 (그리드 기준)
        const eventActualStartIdx = findGridIndex(gridDays, event.start);
        const eventActualEndIdx = findGridIndex(gridDays, event.end);

        // 4. 주 단위로 분할
        let currentIdx = startIdx;
        while (currentIdx <= endIdx) {
            const weekIndex = Math.floor(currentIdx / 7);
            const startCol = currentIdx % 7;

            // 해당 주의 마지막 날 또는 이벤트 종료일 중 작은 값
            const weekEndIdx = Math.min((weekIndex + 1) * 7 - 1, endIdx);
            const endCol = weekEndIdx % 7;

            weeks[weekIndex].push({
                eventId: event.id,
                title: event.title,
                category: event.category,
                weekIndex,
                startCol,
                endCol,
                isStart: currentIdx === eventActualStartIdx || currentIdx === startIdx,
                isEnd: weekEndIdx === eventActualEndIdx || weekEndIdx === endIdx,
                lane: -1, // 나중에 할당
            });

            currentIdx = weekEndIdx + 1;
        }
    }

    return weeks;
}

/**
 * 주 단위 Segment에 Lane 할당 (0~3, 초과 시 -1)
 */
export function assignLanes(weekSegments: WeekSegment[]): WeekSegment[] {
    // 시작 열 기준 정렬, 같으면 길이가 긴 것 우선
    const sorted = [...weekSegments].sort((a, b) => {
        if (a.startCol !== b.startCol) return a.startCol - b.startCol;
        return (b.endCol - b.startCol) - (a.endCol - a.startCol);
    });

    // 각 lane의 마지막 점유 열 추적
    const laneEndCols: number[] = Array(MAX_LANES).fill(-1);

    for (const segment of sorted) {
        // 사용 가능한 가장 낮은 lane 찾기
        let assignedLane = -1;
        for (let lane = 0; lane < MAX_LANES; lane++) {
            if (laneEndCols[lane] < segment.startCol) {
                assignedLane = lane;
                laneEndCols[lane] = segment.endCol;
                break;
            }
        }

        // lane 할당 (4개 모두 점유 시 -1 = overflow)
        segment.lane = assignedLane;
    }

    return sorted;
}

/**
 * 모든 주의 Segment에 Lane 할당
 */
export function assignAllLanes(weeks: WeekSegment[][]): WeekSegment[][] {
    return weeks.map(weekSegments => assignLanes(weekSegments));
}

/**
 * Overflow 정보 계산
 */
export function calculateOverflow(
    weeks: WeekSegment[][],
    gridDays: Date[]
): Map<string, DayOverflow> {
    const overflowMap = new Map<string, DayOverflow>();

    for (const week of weeks) {
        // lane이 -1인 segment들이 overflow
        const overflowSegments = week.filter(s => s.lane === -1);

        for (const segment of overflowSegments) {
            const weekStartIdx = segment.weekIndex * 7;

            for (let col = segment.startCol; col <= segment.endCol; col++) {
                const dayIndex = weekStartIdx + col;
                if (dayIndex >= gridDays.length) continue;

                const dateKey = toDateKey(gridDays[dayIndex]);

                const existing = overflowMap.get(dateKey) || {
                    dateKey,
                    count: 0,
                    eventIds: [],
                };
                existing.count++;
                if (!existing.eventIds.includes(segment.eventId)) {
                    existing.eventIds.push(segment.eventId);
                }
                overflowMap.set(dateKey, existing);
            }
        }
    }

    return overflowMap;
}
