// features/home/home.types.ts
export type HomeCategoryKey =
    | "housing"
    | "finance"
    | "job"
    | "education"
    | "youth"
    | "health"
    | "etc";

export const HOME_CATEGORIES: Array<{
    key: HomeCategoryKey;
    label: string;
    icon: string;
}> = [
        { key: "housing", label: "주거", icon: "🏠" },
        { key: "finance", label: "생활·금융", icon: "🐷" },
        { key: "job", label: "일자리", icon: "💼" },
        { key: "education", label: "교육", icon: "💡" },
        { key: "youth", label: "청년지원", icon: "🧑‍🎓" },
        { key: "health", label: "마음건강", icon: "💗" },
        { key: "etc", label: "기타·돌봄", icon: "🫶" },
    ];
