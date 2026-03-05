// features/calendar/calendar.api.ts
import { api } from "@/services/axios";
import {
    CalendarEvent,
    CalendarPeriodMode,
    CalendarApiResponse,
} from "./calendar.types";
import { parseAplyYmdRange, parseYYYYMMDD } from "./calendar.utils";

/**
 * ✅ 달력 이벤트 API 호출
 * - mode: "apply" (신청기간) | "biz" (사업기간)
 * - year, month: 조회할 년/월
 *
 * ⚠️ 에러 전략: throw (호출부에서 try-catch + 에러 UI 필수)
 * → 네트워크/API 에러 시 예외를 그대로 전파하여 호출부가 상황에 맞는 에러 표시를 제어합니다.
 */
export async function fetchCalendarEvents(
    mode: CalendarPeriodMode,
    year: number,
    month: number
): Promise<CalendarEvent[]> {
    const response = await api.get<CalendarApiResponse>("/api/policies/calendar/", {
        params: { mode, year, month },
    });

    const { events } = response.data;

    // DTO → CalendarEvent 변환
    return events.flatMap((dto): CalendarEvent[] => {
        if (mode === "apply") {
            const range = parseAplyYmdRange(dto.aplyYmd ?? "");
            if (!range) return [];

            return [{
                id: dto.plcy_no,
                title: dto.plcy_nm,
                start: range.start,
                end: range.end,
                mode: "apply" as const,
                category: dto.category,
            }];
        }

        // mode === "biz"
        const start = parseYYYYMMDD(dto.bizPrdBgngYmd ?? "");
        const end = parseYYYYMMDD(dto.bizPrdEndYmd ?? "");
        if (!start || !end) return [];

        return [{
            id: dto.plcy_no,
            title: dto.plcy_nm,
            start,
            end,
            mode: "biz" as const,
            category: dto.category,
        }];
    });
}