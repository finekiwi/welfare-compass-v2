// features/home/CategoryMenu.tsx
"use client";

import Image from "next/image";
import { HOME_CATEGORIES } from "./home.types";

export function CategoryMenu() {
  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-center justify-center gap-6">
        {HOME_CATEGORIES.map((c) => {
          const ring = 60;                 // ✅ 링(원형 테두리) 고정 크기
          const icon = c.iconSize ?? 64;    // ✅ 아이콘은 원하는 크기(48 초과 가능)

          return (
            <button
              key={c.key}
              className="flex w-[92px] flex-col items-center gap-2 text-xs text-gray-700"
              type="button"
              onClick={() => console.log("category:", c.key)}
            >
              {/* ✅ 링 기준 좌표계(48 고정) */}
              <span
                className="relative flex items-center justify-center text-gray-600 cursor-pointer"
                style={{ width: ring, height: ring }}
              >
                {/* ✅ 1) 아이콘: 링과 무관하게 크게 (absolute로 가운데 정렬) */}
                <span
                  className="absolute left-1/2 top-1/2 z-0"
                  style={{
                    width: icon,
                    height: icon,
                    transform: "translate(-50%, -50%)", // ✅ 정확히 중앙정렬
                  }}
                >
                  <Image
                    src={c.icon}
                    alt={c.label}
                    fill
                    sizes={`${icon}px`} // ✅ 실제 렌더 크기에 맞춰 힌트
                    className="object-contain"
                  />
                </span>

                {/* ✅ 2) 링: 항상 48 */}
                <span className="pointer-events-none absolute inset-0 z-10 rounded-full border bg-white/10" />
              </span>

              <span>{c.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
