// features/policy/YouthPolicySection.tsx
import { fetchYouthPolicies } from "./policy.api";
import { PolicyCard } from "./PolicyCard";

export async function YouthPolicySection() {
  const policies = await fetchYouthPolicies();

  return (
    <section className="pb-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">청년지원정책</h2>
        <button className="rounded-full border px-4 py-2 text-xs text-gray-700">
          청년지원정책 더보기 &gt;
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {policies.map((p) => (
          <PolicyCard key={p.id} policy={p} />
        ))}
      </div>
    </section>
  );
}
