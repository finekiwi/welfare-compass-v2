// features/policy/policy.types.ts

export type PolicyCategory =
  | "housing"
  | "finance"
  | "job"
  | "entrepreneurship"
  | "mental-health"
  | "emotional-wellbeing"
  | "care-protection";

// 목록/카드용 간략 타입
export type Policy = {
  id: string;
  title: string;
  summary: string;
  category: PolicyCategory;
  region: string;
  target: string;
  period: string;
  criteria: string;
  content: string;
  isPriority?: boolean;
  isYouth?: boolean;
  aplyYmd?: string;
  bizPrdBgngYmd?: string;
  bizPrdEndYmd?: string;
};

// ✅ 상세 페이지용 전체 필드 타입
export type PolicyDetail = {
  // 기본 정보
  id: string;               // plcy_no
  title: string;            // plcy_nm
  description: string;      // plcy_expln_cn
  supportContent: string;   // plcy_sprt_cn

  // 자격 요건
  minAge: number | null;    // sprt_trgt_min_age
  maxAge: number | null;    // sprt_trgt_max_age
  hasAgeLimitYn: string;    // sprt_trgt_age_lmt_yn (Y/N)
  incomeConditionCode: string; // earn_cnd_se_cd
  minIncome: number | null; // earn_min_amt
  maxIncome: number | null; // earn_max_amt
  marriageStatusCode: string; // mrg_stts_cd
  jobCode: string;          // job_cd
  schoolCode: string;       // school_cd

  // 신청 정보
  applyStartDate: string | null;  // aply_start_dt
  applyEndDate: string | null;    // aply_end_dt
  applyMethod: string;      // plcy_aply_mthd_cn
  applyUrl: string;         // aply_url_addr

  // 사업 기간
  bizStartDate: string | null;    // biz_prd_bgng_ymd
  bizEndDate: string | null;      // biz_prd_end_ymd

  // 지역/카테고리
  region: string;           // district
  categories: { id: number; name: string }[];

  // 메타
  createdAt: string | null; // frst_reg_dt
  updatedAt: string | null; // last_mdfcn_dt
};

// ✅ 카드(UI)에 필요한 최소 필드만 뽑은 타입
export type PolicyCardItem = Pick<Policy, "id" | "title" | "summary" | "region" | "category" | "isPriority" | "content">;