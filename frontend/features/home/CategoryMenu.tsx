// features/home/CategoryMenu.tsx
"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { HOME_CATEGORIES } from "./home.types";

export function CategoryMenu() {
  const router = useRouter();

  return (
    <section className="border-b border-gray-200 pb-3">
      <div className="flex flex-wrap items-start justify-center gap-8 lg:gap-12">
        {HOME_CATEGORIES.map((category) => {
          const iconSize = category.iconSize ?? 58;
          return (
            <button
              key={category.key}
              type="button"
              onClick={() => router.push(`/policy?category=${category.key}`)}
              className="group flex w-[95px] flex-col items-center gap-1"
            >
              <span className="relative flex h-[45px] w-[82px] items-center justify-center transition group-hover:border-gray-400 cursor-pointer">
                <span className="relative" style={{ width: iconSize, height: iconSize }}>
                  <Image
                    src={category.icon}
                    alt={category.label}
                    fill
                    sizes={`${iconSize}px`}
                    className="object-contain"
                  />
                </span>
              </span>
              <span className="text-sm font-medium text-gray-800">{category.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
