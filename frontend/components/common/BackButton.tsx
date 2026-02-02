"use client";

import { useRouter } from "next/navigation";

interface BackButtonProps {
    className?: string;
    label?: string;
}

export function BackButton({ className = "", label = "뒤로가기" }: BackButtonProps) {
    const router = useRouter();

    return (
        <button
            onClick={() => router.back()}
            className={`inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 ${className}`}
        >
            {label}
        </button>
    );
}
