import Link from "next/link";
import type { PolicyCard } from "./chatbot.types";

type CategoryToken = {
  label: string;
  className: string;
};

const CATEGORY_TOKENS: Record<string, CategoryToken> = {
  "일자리": { label: "일자리", className: "bg-blue-50 text-blue-700" },
  "주거": { label: "주거", className: "bg-emerald-50 text-emerald-700" },
  "교육": { label: "교육", className: "bg-violet-50 text-violet-700" },
  "복지·문화": { label: "복지·문화", className: "bg-rose-50 text-rose-700" },
  "참여·권리": { label: "참여·권리", className: "bg-amber-50 text-amber-700" },
};

const ELIGIBILITY_TEXT: Record<PolicyCard["eligibility"], string> = {
  eligible: "회원님의 조건에 맞는 정책일 가능성이 높아요.",
  uncertain: "일부 자격조건 확인이 필요해요.",
  ineligible: "현재 조건에서는 제한될 수 있어요.",
};

function normalizeCategory(raw: string): CategoryToken {
  if (!raw) return CATEGORY_TOKENS["복지·문화"];

  if (raw.includes("일자리") || raw.includes("고용") || raw.includes("취업")) {
    return CATEGORY_TOKENS["일자리"];
  }
  if (raw.includes("주거") || raw.includes("월세") || raw.includes("전세")) {
    return CATEGORY_TOKENS["주거"];
  }
  if (raw.includes("교육") || raw.includes("학습") || raw.includes("훈련")) {
    return CATEGORY_TOKENS["교육"];
  }
  if (raw.includes("참여") || raw.includes("권리") || raw.includes("활동")) {
    return CATEGORY_TOKENS["참여·권리"];
  }
  return CATEGORY_TOKENS["복지·문화"];
}

function truncateOneLine(text: string, max = 62): string {
  const compact = decodeAndCleanText(text).replace(/\s+/g, " ").trim();
  if (!compact) return "정보가 준비 중입니다.";
  if (compact.length <= max) return compact;
  return `${compact.slice(0, max)}...`;
}

function decodeAndCleanText(text: string): string {
  return text
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/[○●•▪◦□ㅁ]/g, " ")
    .replace(/<[^>]*>/g, " ");
}

function BenefitIcon() {
  return (
    <span className="mr-1 inline-grid h-5 w-5 place-items-center rounded-full bg-amber-100 align-[-2px]">
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-amber-600" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 3l1.8 3.6L18 8.4l-3 2.9.7 4.1-3.7-1.9L8.3 15.4l.7-4.1-3-2.9 4.2-.8L12 3z" />
      </svg>
    </span>
  );
}

function TargetIcon() {
  return (
    <span className="mr-1 inline-grid h-5 w-5 place-items-center rounded-full bg-emerald-100 align-[-2px]">
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-emerald-600" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="8" r="3" />
        <path d="M5 20a7 7 0 0114 0" />
        <path d="M18 14l2 2 3-3" />
      </svg>
    </span>
  );
}

function ApplyIcon() {
  return (
    <span className="mr-1 inline-grid h-5 w-5 place-items-center rounded-full bg-blue-100 align-[-2px]">
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-blue-600" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 3h7v7" />
        <path d="M10 14L21 3" />
        <path d="M21 14v5a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h5" />
      </svg>
    </span>
  );
}

function toApplyHost(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function toTargetLine(policy: PolicyCard): string {
  if (policy.eligibility === "ineligible" && policy.ineligible_reasons.length > 0) {
    return truncateOneLine(policy.ineligible_reasons.join(" · "), 58);
  }
  return ELIGIBILITY_TEXT[policy.eligibility];
}

function DdayBadge({ dday }: { dday: number | null }) {
  if (dday === null) return null;
  if (dday < 0) return <span className="text-xs text-gray-400">마감</span>;
  if (dday === 0) return <span className="text-xs font-semibold text-red-600">D-day</span>;
  return <span className="text-xs font-semibold text-blue-600">D-{dday}</span>;
}

export function PolicyCardItem({ policy }: { policy: PolicyCard }) {
  const category = normalizeCategory(policy.category);
  const detailHref = policy.plcy_no ? `/policy/${policy.plcy_no}` : null;

  const benefitLine = truncateOneLine(policy.summary || "지원 내용은 상세페이지에서 확인해 주세요.", 999);
  const targetLine = toTargetLine(policy);
  const applyHost = toApplyHost(policy.apply_url);

  return (
    <article className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-2">
        <span className={`inline-flex rounded-xl px-3 py-1 text-xs font-semibold ${category.className}`}>
          {category.label}
        </span>
        <DdayBadge dday={policy.dday} />
      </div>

      <h4 className="mb-2 line-clamp-2 text-base font-extrabold leading-snug text-gray-900">
        {policy.plcy_nm || "정책명 없음"}
      </h4>

      <div className="space-y-1 text-[15px] text-gray-700">
        <p className="flex items-center gap-1">
          <BenefitIcon />
          <span className="shrink-0 font-semibold">혜택:</span>
          <span className="min-w-0 flex-1 truncate">{benefitLine}</span>
        </p>
        <p className="flex items-center gap-1">
          <TargetIcon />
          <span className="shrink-0 font-semibold">대상:</span>
          <span className="min-w-0 flex-1 truncate">{targetLine}</span>
        </p>
        <p className="flex items-center gap-1">
          <ApplyIcon />
          <span className="shrink-0 font-semibold">신청:</span>
          {policy.apply_url && applyHost ? (
            <span className="min-w-0 flex-1 truncate">
              <span>온라인 접수 (</span>
              <a
                href={policy.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-700 underline"
                title={applyHost}
              >
                {applyHost}
              </a>
              <span>)</span>
            </span>
          ) : policy.apply_url ? (
            <span className="min-w-0 flex-1 truncate">온라인 접수</span>
          ) : (
            <span className="min-w-0 flex-1 truncate">상세페이지에서 신청 방법을 확인해 주세요.</span>
          )}
        </p>
      </div>

      <div className="mt-3">
        {detailHref ? (
          <Link
            href={detailHref}
            className="inline-flex rounded-xl border border-blue-200 px-3 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-50"
          >
            자세히보기
          </Link>
        ) : (
          <span className="text-sm text-gray-400">상세 링크 없음</span>
        )}
      </div>
    </article>
  );
}
