"use client";

import { useEffect } from "react";
import { useFontStore } from "@/stores/font.store";

export function FontSizeManager() {
    const size = useFontStore((state) => state.size);

    useEffect(() => {
        // 1rem = 16px (default) -> html font-size % 조정으로 rem 단위 전체 스케일링
        document.documentElement.style.fontSize = `${size}%`;
    }, [size]);

    return null;
}
