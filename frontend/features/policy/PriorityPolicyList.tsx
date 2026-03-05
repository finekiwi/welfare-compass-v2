// features/policy/PriorityPolicyList.tsx
import Link from "next/link";
import { PolicyCard } from "./PolicyCard";
import { fetchPriorityPolicyCards } from "./policy.api";

export async function PriorityPolicyList() {
  const policies = await fetchPriorityPolicyCards(4);

  return (
    <section className="mb-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">복지정책 우선순위(n)</h2>
        <Link href="/policy" className="text-xs text-blue-800 hover:underline">
          전체 보기
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {policies.map((p) => (
          <PolicyCard key={p.id} policy={p} />
        ))}
      </div>
    </section>
  );
}
