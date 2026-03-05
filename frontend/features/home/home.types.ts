// features/home/home.types.ts

export type HomeCategoryKey =
    | "job"
    | "housing"
    | "education"
    | "welfare"
    | "participation";

export type HomeCategory = {
    key: HomeCategoryKey;
    label: string;
    icon: string;       // 이미지 경로
    iconSize?: number;  // ✅ 항목별 아이콘 크기(px). 없으면 기본값 사용
};

export const HOME_CATEGORIES: HomeCategory[] = [
    { key: "job", label: "일자리", icon: "/icons/home/job.png", iconSize: 65 },
    { key: "housing", label: "주거", icon: "/icons/home/housing.png", iconSize: 65 },
    { key: "education", label: "교육", icon: "/icons/home/entrepreneurship.png", iconSize: 66 },
    { key: "welfare", label: "복지·문화", icon: "/icons/home/emotional-wellbeing.png", iconSize: 52 },
    { key: "participation", label: "참여·권리", icon: "/icons/home/participation.png", iconSize: 60 },
];
