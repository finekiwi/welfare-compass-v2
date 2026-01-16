// features/calendar/constants/categoryColors.ts

export const CATEGORY_COLORS: Record<string, { bg: string; text: string; hover: string; border: string }> = {
    "주거": {
        bg: "bg-blue-100",
        text: "text-blue-700",
        hover: "hover:bg-blue-200",
        border: "border-blue-300"
    },
    "금융": {
        bg: "bg-green-100",
        text: "text-green-700",
        hover: "hover:bg-green-200",
        border: "border-green-300"
    },
    "일자리": {
        bg: "bg-orange-100",
        text: "text-orange-700",
        hover: "hover:bg-orange-200",
        border: "border-orange-300"
    },
    "창업": {
        bg: "bg-purple-100",
        text: "text-purple-700",
        hover: "hover:bg-purple-200",
        border: "border-purple-300"
    },
    "교육": {
        bg: "bg-yellow-100",
        text: "text-yellow-700",
        hover: "hover:bg-yellow-200",
        border: "border-yellow-300"
    },
    "복지": {
        bg: "bg-pink-100",
        text: "text-pink-700",
        hover: "hover:bg-pink-200",
        border: "border-pink-300"
    },
    "문화": {
        bg: "bg-indigo-100",
        text: "text-indigo-700",
        hover: "hover:bg-indigo-200",
        border: "border-indigo-300"
    },
    "default": {
        bg: "bg-gray-100",
        text: "text-gray-700",
        hover: "hover:bg-gray-200",
        border: "border-gray-300"
    },
};

export function getCategoryColor(category?: string) {
    return CATEGORY_COLORS[category ?? ""] || CATEGORY_COLORS["default"];
}
