// features/policy/policy.types.ts
export type PolicyTag = "청년" | "주거" | "금융" | "일자리" | "교육" | "복지";

export interface Policy {
  id: string;
  title: string;
  tag: PolicyTag;
  summary?: string;
  imageVariant?: "family" | "study" | "care"; // ✅ 지금은 일러스트 대체용
}
