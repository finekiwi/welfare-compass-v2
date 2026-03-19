// features/policy/YouthPolicySection.tsx
import Link from "next/link";
import { PolicyCard } from "./PolicyCard";
import { fetchYouthPolicyCards } from "./policy.api";

export async function YouthPolicySection() {
  const policies = await fetchYouthPolicyCards(8);

  return (
    <section className="pb-10">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">청년지원정책</h2>
        <Link href="/policy" className="rounded-full border border-gray-500 px-5 py-2 text-sm text-gray-700 hover:bg-gray-50 cursor-pointer">
          청년지원정책 더보기 &gt;
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {policies.map((policy) => (
          <PolicyCard key={policy.id} policy={policy} />
        ))}
      </div>
    </section>
  );
}
