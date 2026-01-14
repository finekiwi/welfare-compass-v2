// app/policy/[id]/page.tsx
import { notFound } from "next/navigation";
import { fetchPolicyById } from "@/features/policy/policy.api";

export default async function PolicyDetailPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const policy = await fetchPolicyById(id);

    if (!policy) notFound();

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* ✅ 스크린샷 느낌: 상단 회색 박스 + 제목 */}
            <section className="mx-auto w-full max-w-[980px] rounded-xl bg-gray-100 p-8">
                <h1 className="text-2xl font-semibold">{policy.title}</h1>
                <div className="mt-4 h-px w-full bg-gray-300" />

                {/* ✅ 항목들 (모집기간/지원대상/선정기준/지원내용) */}
                <div className="mt-8 space-y-10 text-sm">
                    <div className="flex gap-10">
                        <div className="w-28 font-semibold">모집기간</div>
                        <div className="text-gray-700">{policy.period}</div>
                    </div>

                    <div className="flex gap-10">
                        <div className="w-28 font-semibold">지원대상</div>
                        <div className="text-gray-700">{policy.target}</div>
                    </div>

                    <div className="flex gap-10">
                        <div className="w-28 font-semibold">선정기준</div>
                        <div className="text-gray-700">{policy.criteria}</div>
                    </div>

                    <div className="flex gap-10">
                        <div className="w-28 font-semibold">지원내용</div>
                        <div className="whitespace-pre-line text-gray-700">{policy.content}</div>
                    </div>
                </div>

                <div className="mt-16 h-px w-full bg-gray-300" />
            </section>
        </div>
    );
}
