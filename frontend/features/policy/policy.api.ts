// features/policy/policy.api.ts
import { MOCK_POLICIES } from "./policy.mock";
import type { Policy, PolicyCategory, PolicyCardItem } from "./policy.types";

export type PolicySearchParams = {
  q?: string;
  category?: PolicyCategory | "all";
  region?: string;
};

// ✅ 카드용으로 축약하는 변환기(실무에서 흔함: DTO -> ViewModel)
function toCardItem(p: Policy): PolicyCardItem {
  return {
    id: p.id,
    title: p.title,
    summary: p.summary,
    region: p.region,
    category: p.category,
    isPriority: p.isPriority,
  };
}

/**
 * ✅ 검색 페이지용 (필터링 때문에 Policy 전체 유지 가능)
 */
export async function fetchPolicies(params?: PolicySearchParams): Promise<Policy[]> {
  const q = (params?.q ?? "").trim().toLowerCase();
  const category = params?.category ?? "all";
  const region = (params?.region ?? "").trim();

  let list = [...MOCK_POLICIES];

  if (category !== "all") list = list.filter((p) => p.category === category);
  if (region) list = list.filter((p) => p.region.includes(region));

  if (q) {
    list = list.filter((p) => {
      const hay = `${p.title} ${p.summary} ${p.target} ${p.content}`.toLowerCase();
      return hay.includes(q);
    });
  }

  await new Promise((r) => setTimeout(r, 150));
  return list;
}

/**
 * ✅ 상세 페이지용
 */
export async function fetchPolicyById(id: string): Promise<Policy | null> {
  await new Promise((r) => setTimeout(r, 80));
  return MOCK_POLICIES.find((p) => p.id === id) ?? null;
}

/**
 * ✅ 메인: 우선순위(카드용으로 반환)
 */
export async function fetchPriorityPolicyCards(limit = 8): Promise<PolicyCardItem[]> {
  const list = MOCK_POLICIES.filter((p) => p.isPriority).slice(0, limit);
  return list.map(toCardItem);
}

/**
 * ✅ 메인: 청년지원(카드용으로 반환)
 */
export async function fetchYouthPolicyCards(limit = 6): Promise<PolicyCardItem[]> {
  const list = MOCK_POLICIES.filter((p) => p.isYouth).slice(0, limit);
  return list.map(toCardItem);
}
