// features/policy/policy.api.ts
import { api } from "@/services/axios";
import type { Policy, PolicyCategory, PolicyCardItem, PolicyDetail } from "./policy.types";

export type PolicySearchParams = {
  q?: string;
  category?: PolicyCategory | "all";
  region?: string;
  page?: number;
  page_size?: number;
};

// 백엔드 응답 타입
interface PolicyListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: BackendPolicy[];
}

interface BackendPolicy {
  plcy_no: string;
  plcy_nm: string;
  plcy_expln_cn?: string;
  plcy_sprt_cn?: string;
  sprt_trgt_min_age?: number | null;
  sprt_trgt_max_age?: number | null;
  sprt_trgt_age_lmt_yn?: string;
  earn_cnd_se_cd?: string;
  earn_min_amt?: number | null;
  earn_max_amt?: number | null;
  mrg_stts_cd?: string;
  job_cd?: string;
  school_cd?: string;
  aply_start_dt?: string | null;
  aply_end_dt?: string | null;
  plcy_aply_mthd_cn?: string;
  aply_url_addr?: string;
  biz_prd_bgng_ymd?: string | null;
  biz_prd_end_ymd?: string | null;
  district?: string;
  categories: { id: number; name: string }[];
  frst_reg_dt?: string | null;
  last_mdfcn_dt?: string | null;
}

// 백엔드 → 프론트엔드 Policy 변환 (목록용)
function toPolicy(bp: BackendPolicy): Policy {
  const categoryMap: Record<string, PolicyCategory> = {
    "일자리": "job",
    "주거": "housing",
    "교육": "education",
    "복지문화": "welfare",
    "참여권리": "participation",
    // Fallbacks for safety or old data
    "금융": "welfare",
    "창업": "job",
    "복지": "welfare",
    "문화": "welfare",
  };

  const categories: PolicyCategory[] = (bp.categories || [])
    .map((c) => categoryMap[c.name] || "welfare")
    .filter((c, i, arr) => arr.indexOf(c) === i); // 중복 제거

  if (categories.length === 0) {
    categories.push("welfare");
  }

  const category = categories[0];

  let period = "상시";
  if (bp.aply_start_dt && bp.aply_end_dt) {
    period = `${bp.aply_start_dt} ~ ${bp.aply_end_dt}`;
  } else if (bp.aply_end_dt) {
    period = `~ ${bp.aply_end_dt}`;
  }

  return {
    id: bp.plcy_no,
    title: bp.plcy_nm,
    summary: bp.plcy_expln_cn?.slice(0, 100) ?? "정책 설명이 없습니다.",
    category,
    categories, // ✅ 다중 카테고리
    region: bp.district || "전국",
    target: `${bp.sprt_trgt_min_age ?? ""}~${bp.sprt_trgt_max_age ?? ""}세` || "전 연령",
    period,
    criteria: "별도 기준 없음",
    content: bp.plcy_sprt_cn ?? bp.plcy_expln_cn ?? "",
  };
}

// 백엔드 → 프론트엔드 PolicyDetail 변환 (상세용)
function toPolicyDetail(bp: BackendPolicy): PolicyDetail {
  return {
    id: bp.plcy_no,
    title: bp.plcy_nm,
    description: bp.plcy_expln_cn ?? "",
    supportContent: bp.plcy_sprt_cn ?? "",

    minAge: bp.sprt_trgt_min_age ?? null,
    maxAge: bp.sprt_trgt_max_age ?? null,
    hasAgeLimitYn: bp.sprt_trgt_age_lmt_yn ?? "N",
    incomeConditionCode: bp.earn_cnd_se_cd ?? "",
    minIncome: bp.earn_min_amt ?? null,
    maxIncome: bp.earn_max_amt ?? null,
    marriageStatusCode: bp.mrg_stts_cd ?? "",
    jobCode: bp.job_cd ?? "",
    schoolCode: bp.school_cd ?? "",

    applyStartDate: bp.aply_start_dt ?? null,
    applyEndDate: bp.aply_end_dt ?? null,
    applyMethod: bp.plcy_aply_mthd_cn ?? "",
    applyUrl: bp.aply_url_addr ?? "",

    bizStartDate: bp.biz_prd_bgng_ymd ?? null,
    bizEndDate: bp.biz_prd_end_ymd ?? null,

    region: bp.district ?? "전국",
    categories: bp.categories ?? [],

    createdAt: bp.frst_reg_dt ?? null,
    updatedAt: bp.last_mdfcn_dt ?? null,
  };
}

// 카드용으로 축약
function toCardItem(p: Policy): PolicyCardItem {
  return {
    id: p.id,
    title: p.title,
    summary: p.summary,
    region: p.region,
    category: p.category,
    categories: p.categories, // ✅ 다중 카테고리 전달
    isPriority: p.isPriority,
    content: p.content,
  };
}

/**
 * ✅ 검색 페이지용 정책 목록
 */
/**
 * ✅ 검색 페이지용 정책 목록
 */
export async function fetchPolicies(
  params?: PolicySearchParams
): Promise<{ policies: Policy[]; totalCount: number }> {
  try {
    const response = await api.get<PolicyListResponse>("/api/policies/", {
      params: {
        search: params?.q,
        category: params?.category === "all" ? undefined : params?.category,
        district: params?.region,  // [FIX] 백엔드 filterset_fields는 'district' 사용
        page: params?.page || 1,
        page_size: params?.page_size || 12, // ✅ 페이지 크기 파라미터 적용
      },
    });

    return {
      policies: response.data.results.map(toPolicy),
      totalCount: response.data.count,
    };
  } catch (error) {
    console.error("fetchPolicies error:", error);
    return { policies: [], totalCount: 0 };
  }
}

/**
 * ✅ 상세 페이지용 (전체 필드)
 */
export async function fetchPolicyById(id: string): Promise<Policy | null> {
  try {
    const response = await api.get<BackendPolicy>(`/api/policies/${id}/`);
    return toPolicy(response.data);
  } catch (error) {
    console.error("fetchPolicyById error:", error);
    return null;
  }
}

/**
 * ✅ 상세 페이지용 (전체 필드 - PolicyDetail 타입)
 */
export async function fetchPolicyDetailById(id: string): Promise<PolicyDetail | null> {
  try {
    const response = await api.get<BackendPolicy>(`/api/policies/${id}/`);
    return toPolicyDetail(response.data);
  } catch (error) {
    console.error("fetchPolicyDetailById error:", error);
    return null;
  }
}

/**
 * ✅ 메인: 마감임박 정책 (우선순위)
 */
export async function fetchPriorityPolicyCards(limit = 8): Promise<PolicyCardItem[]> {
  try {
    const response = await api.get<BackendPolicy[]>("/api/policies/deadline_soon/");
    const policies = response.data?.slice(0, limit).map(toPolicy) || [];
    return policies.map((p) => ({ ...toCardItem(p), isPriority: true }));
  } catch (error) {
    console.error("fetchPriorityPolicyCards error:", error);
    return [];
  }
}

/**
 * ✅ 메인: 청년정책 (일반 목록에서 필터링)
 */
export async function fetchYouthPolicyCards(limit = 6): Promise<PolicyCardItem[]> {
  try {
    const response = await api.get<PolicyListResponse>("/api/policies/", {
      params: { search: "청년", page_size: limit },
    });

    // 🛑 RAW 데이터 확인
    if (response.data?.results?.length > 0) {
      console.log("🔥 RAW API Response [0]:", response.data.results[0]);
    }

    return response.data?.results?.slice(0, limit).map(toPolicy).map(toCardItem) || [];
  } catch (error) {
    console.error("fetchYouthPolicyCards error:", error);
    return [];
  }
}

// =========================================================================
// [맞춤추천 API] - 로그인 필수
// =========================================================================

interface RecommendedPolicyItem extends BackendPolicy {
  match_score: number;
}

interface RecommendedPoliciesResponse {
  count: number;
  profile_summary: {
    age: number | null;
    district: string;
    housing_type: string;
    job_status: string;
    interests: string[];
    special_conditions: string[];
  };
  results: RecommendedPolicyItem[];
}

export type RecommendedPolicyParams = {
  category?: string;
  exclude?: string[];  // 제외할 정책 ID 배열
  limit?: number;      // (deprecated) -> page_size로 대체
  page?: number;       // 페이지 번호
  page_size?: number;  // 페이지당 개수
};

/**
 * ✅ 맞춤추천 정책 목록 (로그인 필수)
 * 
 * 백엔드: GET /api/policies/recommended/
 * - 사용자 프로필 기반 매칭 점수 계산
 * - 인증 토큰 필요 (axios interceptor에서 자동 주입)
 * - [BRAIN4-35] 서버 사이드 페이지네이션 지원
 */
export async function fetchRecommendedPolicies(
  params?: RecommendedPolicyParams
): Promise<{
  policies: (PolicyCardItem & { matchScore: number })[];
  profileSummary: RecommendedPoliciesResponse["profile_summary"];
  totalCount: number;
}> {
  try {
    const response = await api.get<RecommendedPoliciesResponse>(
      "/api/policies/recommended/",
      {
        params: {
          category: params?.category,
          exclude: params?.exclude?.join(","),
          page: params?.page || 1,
          page_size: params?.page_size || params?.limit || 12, // limit 호환성
        },
      }
    );

    const policies = response.data.results.map((item) => ({
      ...toCardItem(toPolicy(item)),
      matchScore: item.match_score,
    }));

    return {
      policies,
      profileSummary: response.data.profile_summary,
      totalCount: response.data.count,
    };
  } catch (error) {
    console.error("fetchRecommendedPolicies error:", error);
    throw error; // 에러는 호출하는 쪽에서 처리 (401 등)
  }
}
