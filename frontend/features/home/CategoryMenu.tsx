// features/home/CategoryMenu.tsx
"use client";

import Image from "next/image";
import { HOME_CATEGORIES } from "./home.types";

export function CategoryMenu() {
  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-center justify-center gap-6">
        {HOME_CATEGORIES.map((c) => {
          const size = c.iconSize ?? 48;

          return (
            <button
              key={c.key}
              className="flex w-[92px] flex-col items-center gap-2 text-sm text-gray-700"
              type="button"
              onClick={() => console.log("category:", c.key)}
            >
              {/* ✅ 레이어링을 위한 relative 래퍼 */}
              <span className="relative flex h-12 w-12 items-center justify-center">
                {/* ✅ 1) 이미지(밑 레이어) */}
                <Image
                  src={c.icon}
                  alt={c.label}
                  width={size}
                  height={size}
                  className="z-0 object-contain"
                />

                {/* ✅ 2) 원형 테두리/배경(위 레이어) */}
                <span
                  className="
                    pointer-events-none
                    absolute inset-0
                    rounded-full border bg-white/10
                    z-10
                  "
                />
              </span>

              <span>{c.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
