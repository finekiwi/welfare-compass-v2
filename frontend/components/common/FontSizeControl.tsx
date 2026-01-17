"use client";

import { useFontStore } from "@/stores/font.store";

export function FontSizeControl() {
    const { size, increase, decrease, reset } = useFontStore();

    return (
        <div className="flex items-center gap-1">
            <button
                onClick={decrease}
                className="flex h-6 w-6 items-center justify-center rounded-full text-xs hover:bg-gray-100 font-bold text-gray-600"
                aria-label="글자 작게"
                title="글자 작게"
            >
                가-
            </button>
            <span className="w-9 text-center text-xs font-medium text-gray-600 tabular-nums">
                {size}%
            </span>
            <button
                onClick={increase}
                className="flex h-6 w-6 items-center justify-center rounded-full text-xs hover:bg-gray-100 font-bold text-gray-600"
                aria-label="글자 크게"
                title="글자 크게"
            >
                가+
            </button>
            {size !== 100 && (
                <button
                    onClick={reset}
                    className="ml-1 h-6 px-1 text-[10px] text-gray-400 hover:text-red-500"
                    title="초기화"
                >
                    ↺
                </button>
            )}
        </div>
    );
}
