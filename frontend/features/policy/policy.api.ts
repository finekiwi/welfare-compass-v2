// features/policy/policy.api.ts
import type { Policy } from "./policy.types";

// ✅ 백엔드 준비 전에는 mock으로 UI부터 완성하는 게 가장 빠릅니다.
// 나중에 Axios로 교체할 때 함수 시그니처만 유지하면, UI는 그대로 재사용 가능.
export async function fetchPriorityPolicies(): Promise<Policy[]> {
  return [
    { id: "1", title: "서울시 청년월세 지원", tag: "청년", imageVariant: "family" },
    { id: "2", title: "구직활동 지원금", tag: "일자리", imageVariant: "study" },
    { id: "3", title: "전세자금 대출 이자 지원", tag: "주거", imageVariant: "care" },
    { id: "4", title: "전세자금 대출 이자 지원", tag: "주거", imageVariant: "care" },
  ];
}

export async function fetchYouthPolicies(): Promise<Policy[]> {
  return [
    { id: "11", title: "서울시 청년월세 지원", tag: "청년", imageVariant: "family" },
    { id: "12", title: "구직활동 지원금", tag: "일자리", imageVariant: "study" },
    { id: "13", title: "전세자금 대출 이자 지원", tag: "주거", imageVariant: "care" },
  ];
}
