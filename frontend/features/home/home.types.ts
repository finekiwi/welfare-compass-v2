// features/home/home.types.ts

export type HomeCategoryKey =
    | "housing"
    | "finance"
    | "job"
    | "entrepreneurship"
    | "mental-health"
    | "emotional-wellbeing"
    | "care-protection";

export type HomeCategory = {
    key: HomeCategoryKey;
    label: string;
    icon: string;       // 이미지 경로
    iconSize?: number;  // ✅ 항목별 아이콘 크기(px). 없으면 기본값 사용
};

export const HOME_CATEGORIES: HomeCategory[] = [
    { key: "housing", label: "주거", icon: "/icons/home/housing.png", iconSize: 48 },
    { key: "finance", label: "생활·금융", icon: "/icons/home/finance.png", iconSize: 48 },
    { key: "job", label: "일자리", icon: "/icons/home/job.png", iconSize: 48 },
    { key: "entrepreneurship", label: "창업", icon: "/icons/home/entrepreneurship.png", iconSize: 48 },
    { key: "mental-health", label: "정신건강", icon: "/icons/home/mental-health.png", iconSize: 61 },
    { key: "emotional-wellbeing", label: "마음건강", icon: "/icons/home/emotional-wellbeing.png", iconSize: 40 },
    { key: "care-protection", label: "보호·돌봄", icon: "/icons/home/care-protection.png", iconSize: 30 },
];
