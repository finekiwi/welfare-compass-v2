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
    return events
        .map((dto) => {
            if (mode === "apply") {
                const range = parseAplyYmdRange(dto.aplyYmd ?? "");
                if (!range) return null;

                return {
                    id: dto.plcy_no,
                    title: dto.plcy_nm,
                    start: range.start,
                    end: range.end,
                    mode: "apply" as const,
                };
            }

            // mode === "biz"
            const start = parseYYYYMMDD(dto.bizPrdBgngYmd ?? "");
            const end = parseYYYYMMDD(dto.bizPrdEndYmd ?? "");
            if (!start || !end) return null;

            return {
                id: dto.plcy_no,
                title: dto.plcy_nm,
                start,
                end,
                mode: "biz" as const,
            };
        })
        .filter((v): v is CalendarEvent => v !== null);
}