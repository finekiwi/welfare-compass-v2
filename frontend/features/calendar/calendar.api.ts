// features/calendar/calendar.api.ts
import { MOCK_POLICIES } from "@/features/policy/policy.mock";
import { CalendarEvent, CalendarPeriodMode } from "./calendar.types";
import { parseAplyYmdRange, parseYYYYMMDD } from "./calendar.utils";
import type { Policy } from "@/features/policy/policy.types";

/**
 * ✅ 달력 이벤트 생성
 * - 기본: 신청기간(aplyYmd) 기준
 * - 옵션: 사업기간(bizPrdBgngYmd~bizPrdEndYmd) 기준
 *
 * 지금은 목업이므로, 정책 데이터에 아래 필드가 "있다"는 가정이 필요해:
 * - (신청) aplyYmd: "YYYYMMDD ~ YYYYMMDD" 형태 문자열
 * - (사업) bizPrdBgngYmd, bizPrdEndYmd: "YYYYMMDD"
 *
 * 아직 Policy 타입에 이 필드들이 없다면, 목업 정책에만 임시로 추가하거나
 * 달력 전용 목업을 따로 둬도 됨.
 */
export async function fetchCalendarEvents(
    mode: CalendarPeriodMode,
): Promise<CalendarEvent[]> {
    await new Promise((r) => setTimeout(r, 120));

    // 목업 정책에 aplyYmd/bizPrdBgngYmd/bizPrdEndYmd가 "추가되어 있다"는 전제
    const policies = MOCK_POLICIES as Array<
        Policy & {
            aplyYmd?: string;
            bizPrdBgngYmd?: string;
            bizPrdEndYmd?: string;
        }
    >;

    if (mode === "apply") {
        return policies
            .map((p) => {
                const range = parseAplyYmdRange(p.aplyYmd ?? "");
                if (!range) return null;

                const ev: CalendarEvent = {
                    id: p.id,
                    title: p.title,
                    start: range.start,
                    end: range.end,
                    mode: "apply",
                };
                return ev;
            })
            .filter((v): v is CalendarEvent => v !== null);
    }

    // mode === "biz"
    return policies
        .map((p) => {
            const start = parseYYYYMMDD(p.bizPrdBgngYmd ?? "");
            const end = parseYYYYMMDD(p.bizPrdEndYmd ?? "");
            if (!start || !end) return null;

            const ev: CalendarEvent = {
                id: p.id,
                title: p.title,
                start,
                end,
                mode: "biz",
            };
            return ev;
        })
        .filter((v): v is CalendarEvent => v !== null);
}