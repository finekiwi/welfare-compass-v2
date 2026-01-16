// features/policy/PolicyCard.tsx
import Link from "next/link";
import Image from "next/image";
import type { PolicyCardItem } from "./policy.types";
import { POLICY_CATEGORY_IMAGE } from "./policy.images";

export function PolicyCard({ policy }: { policy: PolicyCardItem }) {
  // ✅ 이미지 src가 누락돼도 깨지지 않게 fallback 권장
  const imgSrc =
    POLICY_CATEGORY_IMAGE[policy.category] ?? "/images/policy/placeholder.png";

  return (
    <Link
      href={`/policy/${policy.id}`}
      className={[
        "block overflow-hidden rounded-xl border bg-white",
        "transition-shadow hover:shadow-md",
      ].join(" ")}
    >
      {/* ✅ (A) 카드 상단 고정 영역: hover와 무관 */}
      <div className="p-4 pb-3">
        <div className="mb-2 flex items-center gap-2">
          {policy.isPriority && (
            <span className="inline-flex items-center rounded-full bg-yellow-500 px-3 py-1 text-xs font-semibold text-white">
              1순위
            </span>
          )}
          <span className="inline-flex items-center rounded-full border bg-white px-3 py-1 text-xs font-semibold text-gray-900">
            {categoryLabel(policy.category)}
          </span>
        </div>

        <h3 className="line-clamp-2 text-lg font-extrabold tracking-tight text-gray-900">
          {policy.title}
        </h3>
      </div>

      {/* ✅ (B) 이미지 영역: 여기만 hover 오버레이 적용 */}
      <div className="group relative aspect-square w-full">
        <Image
          src={imgSrc}
          alt={`${categoryLabel(policy.category)} 대표 이미지`}
          fill
          className="object-cover"
          priority={false}
        />

        {/* 기본 상태에서 이미지에 살짝 그라데이션(선택) */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/25 to-transparent" />

        {/* ✅ hover 시 요약 오버레이 */}
        <div
          className={[
            "absolute inset-0",
            "bg-white/95",
            "opacity-0 group-hover:opacity-100",
            "transition-opacity duration-200",
          ].join(" ")}
        >
          <div className="flex h-full flex-col p-4">
            <div className="mb-2">
              <span className="rounded border px-2 py-0.5 text-[10px] text-gray-600">
                {policy.region}
              </span>
            </div>

            <p className="whitespace-pre-line text-sm leading-6 text-gray-700">
              {policy.summary}
            </p>

            <div className="mt-auto pt-4 text-xs text-gray-500">
              클릭하면 상세 페이지로 이동
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}

/** 카테고리 라벨(표시용) */
function categoryLabel(category: PolicyCardItem["category"]) {
  switch (category) {
    case "housing":
      return "주거";
    case "finance":
      return "생활·금융";
    case "job":
      return "일자리";
    case "entrepreneurship":
      return "창업";
    case "mental-health":
      return "정신건강";
    case "emotional-wellbeing":
      return "마음건강";
    case "care-protection":
      return "보호·돌봄";
    default:
      return "카테고리";
  }
}
