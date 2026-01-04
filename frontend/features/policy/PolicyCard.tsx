// features/policy/PolicyCard.tsx
import type { Policy } from "./policy.types";

function tagStyle(tag: Policy["tag"]) {
  // ✅ 태그별 배지 스타일 (나중에 디자인 시스템 생기면 교체)
  switch (tag) {
    case "청년":
      return "bg-orange-100 text-orange-700";
    case "주거":
      return "bg-blue-100 text-blue-700";
    case "금융":
      return "bg-emerald-100 text-emerald-700";
    case "일자리":
      return "bg-indigo-100 text-indigo-700";
    case "교육":
      return "bg-yellow-100 text-yellow-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

function imagePlaceholder(variant?: Policy["imageVariant"]) {
  // ✅ 실제 일러스트/썸네일 들어오기 전 임시 박스
  // public 이미지 연결 시 img로 교체
  const label =
    variant === "family" ? "👨‍👩‍👧‍👦" : variant === "study" ? "📚" : "♿️";
  return (
    <div className="flex h-[180px] items-center justify-center rounded-xl bg-gray-50 text-5xl">
      {label}
    </div>
  );
}

export function PolicyCard({ policy }: { policy: Policy }) {
  return (
    <article className="rounded-2xl border bg-white p-3 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span
          className={`rounded-full px-2 py-1 text-xs font-medium ${tagStyle(
            policy.tag
          )}`}
        >
          {policy.tag}
        </span>
      </div>

      {imagePlaceholder(policy.imageVariant)}

      <h3 className="mt-3 line-clamp-2 text-sm font-semibold">{policy.title}</h3>
      {policy.summary ? (
        <p className="mt-1 line-clamp-2 text-xs text-gray-600">{policy.summary}</p>
      ) : null}
    </article>
  );
}
