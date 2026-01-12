// features/policy/PolicyCard.tsx
import Link from "next/link";
import { Policy } from "./policy.types";

/**
 * ✅ 카드 클릭 시 상세 페이지로 이동
 * - /policy/[id]
 */
export function PolicyCard({ policy }: { policy: Policy }) {
  return (
    <Link
      href={`/policy/${policy.id}`}
      className="block rounded-lg border bg-white p-4 hover:bg-gray-50"
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="rounded border px-2 py-0.5 text-[10px] text-gray-600">
          {policy.region}
        </span>
      </div>

      <h3 className="mb-2 line-clamp-1 text-sm font-semibold">{policy.title}</h3>

      <p className="line-clamp-4 text-xs leading-5 text-gray-600">{policy.summary}</p>
    </Link>
  );
}
