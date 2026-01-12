// features/policy/policy.api.ts
import { MOCK_POLICIES } from "./policy.mock";
import { Policy, PolicyCategory } from "./policy.types";

export type PolicySearchParams = {
  q?: string;                 // 키워드
  category?: PolicyCategory | "all";
  region?: string;            // 지금은 단순 문자열
};

/**
 * ✅ 현재: 목업 데이터 조회
 * ✅ 추후: Django(DRF) endpoint 호출로 교체
 *
 * 교체 포인트 예시:
 * - GET /api/policies/?search=...&category=...&region=...
 */
export async function fetchPolicies(params?: PolicySearchParams): Promise<Policy[]> {
  const q = (params?.q ?? "").trim().toLowerCase();
  const category = params?.category ?? "all";
  const region = (params?.region ?? "").trim();

  let list = [...MOCK_POLICIES];

  if (category !== "all") {
    list = list.filter((p) => p.category === category);
  }

  if (region) {
    list = list.filter((p) => p.region.includes(region));
  }

  if (q) {
    list = list.filter((p) => {
      const hay = `${p.title} ${p.summary} ${p.target} ${p.content}`.toLowerCase();
      return hay.includes(q);
    });
  }

  // 서버 통신 흉내(UX 확인용) - 필요 없으면 지워도 됨
  await new Promise((r) => setTimeout(r, 150));

  return list;
}

export async function fetchPolicyById(id: string): Promise<Policy | null> {
  // 서버 통신 흉내
  await new Promise((r) => setTimeout(r, 80));
  return MOCK_POLICIES.find((p) => p.id === id) ?? null;
}

/**
 * ✅ 메인: 우선순위 정책 n개
 * - 지금은 목업의 isPriority를 기준으로 상위 n개 반환
 * - 나중에 Django에서 "rank/score" 내려주면 그대로 교체 가능
 */
export async function fetchPriorityPolicies(limit = 8): Promise<Policy[]> {
  const list = MOCK_POLICIES.filter((p) => p.isPriority);
  return list.slice(0, limit);
}

/**
 * ✅ 메인: 청년지원 정책 n개
 * - isYouth 기준
 */
export async function fetchYouthPolicies(limit = 6): Promise<Policy[]> {
  const list = MOCK_POLICIES.filter((p) => p.isYouth);
  return list.slice(0, limit);
}