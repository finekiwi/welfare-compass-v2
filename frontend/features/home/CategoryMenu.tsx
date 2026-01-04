// features/home/CategoryMenu.tsx
"use client";

import { HOME_CATEGORIES } from "./home.types";

export function CategoryMenu() {
  // ✅ ② 이미지의 동그란 아이콘 카테고리 라인
  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-center justify-center gap-6">
        {HOME_CATEGORIES.map((c) => (
          <button
            key={c.key}
            className="flex w-[92px] flex-col items-center gap-2 text-sm text-gray-700"
            type="button"
            onClick={() => {
              // TODO: 카테고리 필터/이동 로직 연결
              console.log("category:", c.key);
            }}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-full border bg-white">
              {c.icon}
            </span>
            <span>{c.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
