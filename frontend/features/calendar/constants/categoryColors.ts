// features/calendar/constants/categoryColors.ts

export interface CategoryColorSet {
    badge: string;       // 카테고리 뱃지 배경색
    badgeText: string;   // 카테고리 뱃지 글자색
    borderColor: string; // dashed border 색상 (CSS hex)
    bgColor: string;     // 이벤트 배경 색상 (CSS rgba, 아주 연하고 반투명)
    dot: string;         // 범례용 dot 색상
    label: string;       // 카테고리 약어 (뱃지에 표시)
}

export const CATEGORY_COLORS: Record<string, CategoryColorSet> = {
    "일자리": {
        badge: "bg-orange-500",
        badgeText: "text-white",
        borderColor: "#f97316", // orange-500
        bgColor: "#ffedd5cc",     // orange-100 (불투명한 연한 주황색)
        dot: "bg-orange-400",
        label: "일자리",
    },
    "주거": {
        badge: "bg-blue-500",
        badgeText: "text-white",
        borderColor: "#3b82f6", // blue-500
        bgColor: "#e7f0fccc",     // blue-100 (불투명한 연한 파란색)
        dot: "bg-blue-400",
        label: "주거",
    },
    "교육": {
        badge: "bg-yellow-500",
        badgeText: "text-white",
        borderColor: "#eab308", // yellow-500
        bgColor: "#faf4c3cc",     // yellow-100 (불투명한 연한 노란색)
        dot: "bg-yellow-400",
        label: "교육",
    },
    "복지문화": {
        badge: "bg-green-600",
        badgeText: "text-white",
        borderColor: "#16a34a", // green-600
        bgColor: "#d5efdecc",     // green-100 (불투명한 연한 초록색)
        dot: "bg-green-400",
        label: "복지문화",
    },
    "참여권리": {
        badge: "bg-purple-500",
        badgeText: "text-white",
        borderColor: "#a855f7", // purple-500
        bgColor: "#f3e8ffcc",     // purple-100 (불투명한 연한 보라색)
        dot: "bg-purple-400",
        label: "참여권리",
    },
    "default": {
        badge: "bg-gray-500",
        badgeText: "text-white",
        borderColor: "#9ca3af", // gray-400
        bgColor: "#f3f4f6cc",     // gray-100 (불투명한 연한 회색)
        dot: "bg-gray-400",
        label: "기타",
    },
};

export function getCategoryColor(category?: string): CategoryColorSet {
    return CATEGORY_COLORS[category ?? ""] || CATEGORY_COLORS["default"];
}
