// features/policy/PolicyCard.tsx
import Link from "next/link";
import Image from "next/image";
import type { PolicyCardItem } from "./policy.types";
import { POLICY_CATEGORY_IMAGE } from "./policy.images";
import { getCategoryLabel } from "./policy.constants";

export function PolicyCard({ policy, viewMode = "grid" }: { policy: PolicyCardItem, viewMode?: "grid" | "list" }) {
  // ✅ 3단계 이미지 fallback: 포스터 → 카테고리 기본 → 최종 fallback
  const posterUrl = policy.posterUrl; // 관리자 업로드 포스터
  const categoryImg = POLICY_CATEGORY_IMAGE[policy.category] ?? "/images/policy/care-protection.png";

  if (viewMode === "list") {
    return (
      <Link
        href={`/policy/${policy.id}`}
        className="flex flex-col sm:flex-row overflow-hidden rounded border border-gray-300 bg-white transition-colors hover:bg-gray-50 h-auto sm:h-36"
      >
        {/* ✅ (A) 이미지 영역 (좌측 고정 너비) */}
        <div className="relative aspect-[4/3] sm:aspect-auto sm:w-48 shrink-0 bg-gray-100 border-b sm:border-b-0 sm:border-r border-gray-200">
          {posterUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={posterUrl}
              alt={`${getCategoryLabel(policy.category)} 포스터`}
              className="absolute inset-0 h-full w-full object-cover"
            />
          ) : (
            <Image
              src={categoryImg}
              alt={`${getCategoryLabel(policy.category)} 대표 이미지`}
              fill
              className="object-cover"
              priority={false}
            />
          )}

          <div className="absolute top-2 left-2">
            <span className="rounded bg-black/60 px-2 py-0.5 text-[10px] text-white backdrop-blur-sm">
              {policy.region}
            </span>
          </div>
        </div>

        {/* ✅ (B) 텍스트 및 정보 영역 (우측 확장) */}
        <div className="flex flex-1 flex-col p-4 justify-between">
          <div>
            {/* 1. 모집상태 + 카테고리 */}
            <div className="mb-2 flex flex-wrap items-center gap-x-2 text-[13px] font-medium">
              {renderStatusBadge(policy.applyStartDate, policy.applyEndDate)}
              {(() => {
                const rawCats = policy.categories?.length ? policy.categories : [policy.category];
                const cats = rawCats.flatMap((c) => (c || "").split(",")).map((c) => c.trim()).filter(Boolean);
                return cats.map((cat, idx) => (
                  <span key={`${cat}-${idx}`} className="text-gray-500 font-semibold">{getCategoryLabel(cat)}</span>
                ));
              })()}
            </div>

            {/* 2. 정책 제목 */}
            <h3 className="line-clamp-1 text-[17px] font-bold tracking-tight text-gray-900 group-hover:text-blue-600 transition-colors">
              {policy.title}
            </h3>
            
            {/* 3. 설명 (리스트 뷰 전용) */}
            <p className="mt-1.5 line-clamp-2 text-[13px] leading-snug text-gray-500">
              {policy.summary || policy.content || "상세 내용을 확인해 보세요."}
            </p>
          </div>
          
          <div className="mt-2 flex justify-end">
             <span className="text-[11px] font-semibold text-blue-600 hover:underline">상세보기 &rarr;</span>
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={`/policy/${policy.id}`}
      className={[
        "flex flex-col overflow-hidden rounded border border-gray-400 bg-white",
        "transition-shadow",
      ].join(" ")}
    >
      {/* ✅ (A) 텍스트 및 정보 영역 (상단) */}
      <div className="flex flex-1 flex-col px-4 pt-4 pb-2">
        {/* 1. 모집상태 + 카테고리 (한 줄) */}
        <div className="mb-2 flex flex-wrap items-center gap-x-2 text-[13px] font-medium">
          {renderStatusBadge(policy.applyStartDate, policy.applyEndDate)}
          {(() => {
            const rawCats = policy.categories?.length ? policy.categories : [policy.category];
            const cats = rawCats.flatMap((c) => (c || "").split(",")).map((c) => c.trim()).filter(Boolean);
            return cats.map((cat, idx) => (
              <span key={`${cat}-${idx}`} className="text-gray-500">{getCategoryLabel(cat)}</span>
            ));
          })()}
        </div>

        {/* 2. 정책 제목 */}
        <h3 className="line-clamp-2 text-base font-bold leading-snug tracking-tight text-gray-900">
          {policy.title}
        </h3>
      </div>

      {/* ✅ (B) 이미지 영역 (하단, hover 오버레이 포함) */}
      <div className="group relative aspect-[4/3] w-full bg-gray-100 flex-shrink-0">
        {posterUrl ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={posterUrl}
            alt={`${getCategoryLabel(policy.category)} 포스터`}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <Image
            src={categoryImg}
            alt={`${getCategoryLabel(policy.category)} 대표 이미지`}
            fill
            className="object-cover"
            priority={false}
          />
        )}

        {/* 기본 상태에서 이미지에 살짝 그라데이션 */}
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

            {/* 1. 정책 설명 */}
            <div className="mb-2">
              <p className="mb-1 text-[11px] font-bold text-gray-900">정책 설명</p>
              <p className="line-clamp-3 text-xs leading-4 text-gray-600">
                {policy.summary}
              </p>
            </div>

            {/* 2. 지원 내용 */}
            <div>
              <p className="mb-1 text-[11px] font-bold text-gray-900">지원 내용</p>
              <p className="line-clamp-3 text-xs leading-4 text-gray-600">
                {policy.content || "상세 내용을 확인하세요."}
              </p>
            </div>

          </div>
        </div>
      </div>
    </Link>
  );
}

/**
 * 날짜 기반으로 진행상태 뱃지 렌더링
 *
 * ⚠️ new Date("YYYY-MM-DD")는 UTC 자정으로 해석되어 KST(+9)에서
 *    하루 밀리는 버그가 있으므로 parseLocalDate로 로컬 날짜를 생성합니다.
 */
function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d); // 로컬 타임존 기준
}

function renderStatusBadge(startDate: string | null | undefined, endDate: string | null | undefined) {
  if (!startDate && !endDate) {
    return (
      <span className="inline-flex items-center justify-center rounded border border-gray-500 bg-white px-2 py-1 text-[11px] font-bold text-gray-700">
        상시모집
      </span>
    );
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const start = startDate ? parseLocalDate(startDate) : null;
  const end = endDate ? parseLocalDate(endDate) : null;

  if (start && start > today) {
    return (
      <span className="inline-flex items-center justify-center rounded border border-gray-500 bg-white px-2 py-1 text-[11px] font-bold text-gray-700">
        모집예정
      </span>
    );
  }

  if (end && end < today) {
    return (
      <span className="inline-flex items-center justify-center rounded border border-gray-500 px-2 py-1 text-[11px] font-bold text-gray-700">
        마감
      </span>
    );
  }

  if (end) {
    const diffTime = end.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 7) {
      if (diffDays === 0) {
        return (
          <span className="inline-flex items-center justify-center rounded border border-gray-500 bg-white px-3 py-1 text-xs font-bold text-gray-700">
            D-Day
          </span>
        );
      }
      return (
        <span className="inline-flex items-center justify-center rounded border border-gray-500 bg-white px-3 py-1 text-xs font-bold text-gray-700">
          D-{diffDays}
        </span>
      );
    }
  }

  return (
    <span className="inline-flex items-center justify-center rounded border border-gray-500 bg-white px-3 py-1 text-xs font-bold text-gray-700">
      모집중
    </span>
  );
}
