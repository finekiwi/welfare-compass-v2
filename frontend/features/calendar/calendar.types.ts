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
  category?: string;       // 카테고리 (색상용)
};

// 주 단위 Segment (A안 오버레이용)
export interface WeekSegment {
  eventId: string;
  title: string;
  category?: string;

  weekIndex: number;     // 0~5 (어느 주인지)
  startCol: number;      // 0~6 (시작 열, 일요일=0)
  endCol: number;        // 0~6 (종료 열, 포함)

  isStart: boolean;      // 이벤트의 시작 주인지
  isEnd: boolean;        // 이벤트의 종료 주인지

  lane: number;          // 0~3 (할당된 줄 번호), -1 = overflow
}

// Overflow 정보
export interface DayOverflow {
  dateKey: string;       // "YYYY-MM-DD"
  count: number;         // 초과된 이벤트 수
  eventIds: string[];    // 해당 날짜의 overflow 이벤트 ID들
}

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
