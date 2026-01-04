// features/policy/PriorityPolicyList.tsx
import { fetchPriorityPolicies } from "./policy.api";
import { PolicyCard } from "./PolicyCard";

export async function PriorityPolicyList() {
  // ✅ 서버 컴포넌트에서 mock 데이터를 읽어 카드 렌더
  // 나중에 실제 API가 생겨도 fetch 함수만 바꾸면 됩니다.
  const policies = await fetchPriorityPolicies();

  return (
    <section className="mb-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">복지정책 우선순위(n)</h2>
        <button className="text-xs text-blue-600" type="button">
          비교군 및 맞춤형 보기
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {policies.map((p) => (
          <PolicyCard key={p.id} policy={p} />
        ))}
      </div>
    </section>
  );
}
