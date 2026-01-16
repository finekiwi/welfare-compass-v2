// features/calendar/calendar.types.ts

export type CalendarPeriodMode = "apply" | "biz";
// apply: 신청기간(aplyYmd)
// biz: 사업기간(bizPrdBgngYmd~bizPrdEndYmd)

export type CalendarEvent = {
  id: string;              // policy id
  title: string;           // policy title
  start: Date;             // 이벤트 시작일
  end: Date;               // 이벤트 종료일(포함)
  mode: CalendarPeriodMode;
};

// 백엔드 API 응답 DTO
export interface CalendarEventDTO {
  plcy_no: string;
  plcy_nm: string;
  aplyYmd?: string;
  bizPrdBgngYmd?: string;
  bizPrdEndYmd?: string;
}

export interface CalendarApiResponse {
  year: number;
  month: number;
  mode: CalendarPeriodMode;
  count: number;
  events: CalendarEventDTO[];
}
