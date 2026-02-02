// app/policy/[id]/page.tsx
import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchPolicyDetailById } from "@/features/policy/policy.api";
import { ScrapButton } from "@/features/policy/ScrapButton";
import { BackButton } from "@/components/common/BackButton";

export default async function PolicyDetailPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const policy = await fetchPolicyDetailById(id);

    if (!policy) notFound();

    // 기간 포맷팅
    const formatDate = (date: string | null) => {
        if (!date) return "-";
        return date;
    };

    const applyPeriod =
        policy.applyStartDate && policy.applyEndDate
            ? `${formatDate(policy.applyStartDate)} ~ ${formatDate(policy.applyEndDate)}`
            : policy.applyEndDate
                ? `~ ${formatDate(policy.applyEndDate)}`
                : "상시";

    const bizPeriod =
        policy.bizStartDate && policy.bizEndDate
            ? `${formatDate(policy.bizStartDate)} ~ ${formatDate(policy.bizEndDate)}`
            : "-";

    // 나이 포맷팅
    const ageRange =
        policy.minAge || policy.maxAge
            ? `${policy.minAge ?? ""}세 ~ ${policy.maxAge ?? ""}세`
            : "제한 없음";

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            {/* ✅ 상단 헤더 */}
            <section className="mx-auto w-full max-w-[980px]">
                {/* 뒤로가기 */}
                <BackButton className="mb-4" />

                {/* 카테고리 태그 */}
                <div className="flex items-center gap-2 mb-3">
                    {policy.categories.map((cat) => (
                        <span
                            key={cat.id}
                            className="rounded-full bg-blue-100 text-blue-700 px-3 py-1 text-xs font-medium"
                        >
                            {cat.name}
                        </span>
                    ))}
                    <span className="rounded-full bg-gray-100 text-gray-600 px-3 py-1 text-xs">
                        {policy.region}
                    </span>
                </div>



                {/* 제목 */}
                <div className="mb-6 flex items-start justify-between gap-4">
                    <h1 className="text-2xl md:text-3xl font-bold text-gray-900">
                        {policy.title}
                    </h1>
                    <ScrapButton policyId={policy.id} className="mt-1" />
                </div>
            </section>

            {/* ✅ 메인 컨텐츠 */}
            <section className="mx-auto w-full max-w-[980px] grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 왼쪽: 상세 정보 */}
                <div className="lg:col-span-2 rounded-xl border p-6 space-y-6">
                    {/* 정책 설명 */}
                    <div className="py-4">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">정책 설명</h2>
                        <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                            {policy.description || "정책 설명이 없습니다."}
                        </p>
                    </div>

                    {/* 지원 내용 */}
                    {policy.supportContent && (
                        <div className="pb-4">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">지원 내용</h2>
                            <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                                {policy.supportContent}
                            </p>
                        </div>
                    )}

                    {/* 신청 방법 */}
                    {policy.applyMethod && (
                        <div className="pb-4">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">신청 방법</h2>
                            <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                                {policy.applyMethod}
                            </p>
                        </div>
                    )}
                </div>

                {/* 오른쪽: 요약 정보 카드 */}
                <div className="space-y-4">
                    {/* 신청 정보 카드 */}
                    <div className="rounded-xl border bg-white p-6">
                        <h3 className="text-sm font-semibold text-gray-900 mb-4">신청 정보</h3>
                        <dl className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <dt className="text-gray-500">신청 기간</dt>
                                <dd className="text-gray-900 font-medium">{applyPeriod}</dd>
                            </div>
                            <div className="flex justify-between">
                                <dt className="text-gray-500">사업 기간</dt>
                                <dd className="text-gray-900">{bizPeriod}</dd>
                            </div>
                        </dl>

                        {/* 신청 버튼 */}
                        {policy.applyUrl && (
                            <a
                                href={policy.applyUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-4 block w-full rounded-lg bg-blue-900 py-3 text-center text-sm font-medium text-white hover:bg-blue-950 transition"
                            >
                                신청하기 →
                            </a>
                        )}
                    </div>

                    {/* 자격 요건 카드 */}
                    <div className="rounded-xl border bg-white p-6">
                        <h3 className="text-sm font-semibold text-gray-900 mb-4">자격 요건</h3>
                        <dl className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <dt className="text-gray-500">연령</dt>
                                <dd className="text-gray-900">{ageRange}</dd>
                            </div>
                            {policy.incomeConditionCode && (
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">소득 조건</dt>
                                    <dd className="text-gray-900">{policy.incomeConditionCode}</dd>
                                </div>
                            )}
                            {(policy.minIncome || policy.maxIncome) && (
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">소득 범위</dt>
                                    <dd className="text-gray-900">
                                        {policy.minIncome?.toLocaleString() ?? "0"}원 ~ {policy.maxIncome?.toLocaleString() ?? "-"}원
                                    </dd>
                                </div>
                            )}
                            {policy.jobCode && (
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">직업 조건</dt>
                                    <dd className="text-gray-900">{policy.jobCode}</dd>
                                </div>
                            )}
                            {policy.schoolCode && (
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">학력 조건</dt>
                                    <dd className="text-gray-900">{policy.schoolCode}</dd>
                                </div>
                            )}
                        </dl>
                    </div>

                    {/* 정책 정보 카드 */}
                    <div className="rounded-xl border bg-gray-50 p-6">
                        <h3 className="text-sm font-semibold text-gray-900 mb-4">정책 정보</h3>
                        <dl className="space-y-2 text-xs text-gray-500">
                            <div className="flex justify-between">
                                <dt>정책번호</dt>
                                <dd className="font-mono">{policy.id}</dd>
                            </div>
                            {policy.createdAt && (
                                <div className="flex justify-between">
                                    <dt>등록일</dt>
                                    <dd>{policy.createdAt}</dd>
                                </div>
                            )}
                            {policy.updatedAt && (
                                <div className="flex justify-between">
                                    <dt>수정일</dt>
                                    <dd>{policy.updatedAt}</dd>
                                </div>
                            )}
                        </dl>
                    </div>
                </div>
            </section>
        </div>
    );
}
