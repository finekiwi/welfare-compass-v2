// features/policy/policy.filters.ts
// 검색 페이지 필터 옵션 상수 (PolicySearchPageClient에서 분리)

import type { PolicyCategory } from "./policy.types";

export const CATEGORY_OPTIONS: Array<{ value: PolicyCategory | "all"; label: string }> = [
    { value: "all", label: "전체" },
    { value: "job", label: "일자리" },
    { value: "housing", label: "주거" },
    { value: "education", label: "교육" },
    { value: "welfare", label: "복지·문화" },
    { value: "participation", label: "참여·권리" },
];

export const SUBCATEGORY_OPTIONS = [
    { value: "", label: "전체 세부분류" },
    { value: "취업", label: "취업" },
    { value: "창업", label: "창업" },
    { value: "재직자", label: "재직자" },
    { value: "건강", label: "건강" },
    { value: "교육비지원", label: "교육비지원" },
    { value: "문화활동", label: "문화활동" },
    { value: "예술인지원", label: "예술인지원" },
    { value: "온라인교육", label: "온라인교육" },
    { value: "미래역량강화", label: "미래역량강화" },
    { value: "전월세 및 주거급여 지원", label: "전월세·주거급여" },
    { value: "주택 및 거주지", label: "주택·거주지" },
    { value: "기숙사", label: "기숙사" },
    { value: "취약계층 및 금융지원", label: "취약계층·금융" },
    { value: "권익보호", label: "권익보호" },
    { value: "청년참여", label: "청년참여" },
    { value: "청년국제교류", label: "청년국제교류" },
    { value: "정책인프라구축", label: "정책인프라" },
];

export const EMPLOYMENT_OPTIONS = [
    { value: "", label: "전체 취업상태" },
    { value: "0013001", label: "재직중" },
    { value: "0013002", label: "자영업자" },
    { value: "0013003", label: "미취업·구직중" },
    { value: "0013004", label: "프리랜서" },
    { value: "0013006", label: "창업준비" },
];

export const EDUCATION_OPTIONS = [
    { value: "", label: "전체 학력" },
    { value: "0049001", label: "고졸 미만" },
    { value: "0049002", label: "고교 재학" },
    { value: "0049004", label: "고졸" },
    { value: "0049005", label: "대학 재학" },
    { value: "0049007", label: "대졸" },
    { value: "0049008", label: "석박사" },
];

export const MARRIAGE_OPTIONS = [
    { value: "", label: "전체 혼인상태" },
    { value: "0055002", label: "미혼" },
    { value: "0055001", label: "기혼" },
];

export const APPLY_STATUS_OPTIONS = [
    { value: "", label: "전체 신청상태" },
    { value: "active", label: "진행중" },
    { value: "upcoming", label: "마감임박" },
    { value: "always", label: "상시모집" },
    { value: "closed", label: "마감" },
];

export const SPECIAL_CONDITIONS = [
    { key: "is_for_single_parent" as const, label: "한부모" },
    { key: "is_for_disabled" as const, label: "장애인" },
    { key: "is_for_low_income" as const, label: "저소득" },
    { key: "is_for_newlywed" as const, label: "신혼부부" },
];
