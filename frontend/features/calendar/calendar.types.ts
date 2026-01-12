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
