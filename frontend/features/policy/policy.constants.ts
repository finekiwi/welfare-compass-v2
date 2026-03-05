// features/policy/policy.constants.ts
// 카테고리 매핑/라벨 공통 상수 (PolicyCard, policy.api.ts 등에서 공유)

import type { PolicyCategory } from "./policy.types";

/**
 * 백엔드 카테고리 이름 → 프론트엔드 PolicyCategory 매핑
 */
export const CATEGORY_NAME_MAP: Record<string, PolicyCategory> = {
    "일자리": "job",
    "주거": "housing",
    "교육": "education",
    "복지문화": "welfare",
    "참여권리": "participation",
    // Fallbacks for old data or grouped categories
    "금융": "welfare",
    "창업": "job",
    "복지": "welfare",
    "문화": "welfare",
};

/**
 * PolicyCategory → 한글 라벨
 */
export const CATEGORY_LABELS: Record<PolicyCategory, string> = {
    job: "일자리",
    housing: "주거",
    education: "교육",
    welfare: "복지·문화",
    participation: "참여·권리",
};

/**
 * 카테고리 라벨 조회 (fallback 포함)
 */
export function getCategoryLabel(category: PolicyCategory | string): string {
    return CATEGORY_LABELS[category as PolicyCategory] ?? "카테고리";
}
