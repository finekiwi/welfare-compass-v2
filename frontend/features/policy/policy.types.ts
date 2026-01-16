// features/policy/policy.types.ts

export type PolicyCategory =
  | "housing"
  | "finance"
  | "job"
  | "entrepreneurship"
  | "mental-health"
  | "emotional-wellbeing"
  | "care-protection";

export type Policy = {
  id: string;                // ✅ 상세 라우팅에 쓰일 고유 id (Django pk로 바꿔도 됨)
  title: string;             // 정책명
  summary: string;           // 카드에 보일 짧은 설명
  category: PolicyCategory;  // 카테고리 필터용
  region: string;            // 예: "서울시"
  target: string;            // 지원대상
  period: string;            // 모집기간
  criteria: string;          // 선정기준
  content: string;           // 지원내용(상세)

  // ✅ 메인 섹션에서 쓸 메타(목업/추후 백엔드 필드로 대체 가능)
  isPriority?: boolean; // 우선순위 노출용
  isYouth?: boolean;    // 청년지원 섹션 노출용

  // ✅ 달력용 임시 필드(나중에 Django에서 내려주면 그대로 교체)
  aplyYmd?: string;          // "20260105 ~ 20260215"
  bizPrdBgngYmd?: string;    // "20260220"
  bizPrdEndYmd?: string;     // "20261231"
};

// ✅ 카드(UI)에 필요한 최소 필드만 뽑은 타입
export type PolicyCardItem = Pick<Policy, "id" | "title" | "summary" | "region" | "category" | "isPriority">;