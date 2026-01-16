// features/calendar/components/OverflowButton.tsx
"use client";

interface OverflowButtonProps {
    col: number;
    count: number;
    onClick: () => void;
}

export function OverflowButton({ col, count, onClick }: OverflowButtonProps) {
    // 위치 계산
    const left = `calc(${col} * (100% / 7) + 4px)`;

    return (
        <button
            type="button"
            className="
        absolute z-30 h-[16px] px-1.5
        text-[10px] text-gray-600
        bg-white border border-gray-300 rounded
        hover:bg-gray-100 hover:border-gray-400
        cursor-pointer transition-colors
      "
            style={{
                left,
                top: "calc(4 * 22px + 32px)", // lane 4 위치 (overflow 위치)
            }}
            onClick={onClick}
        >
            +{count}
        </button>
    );
}
