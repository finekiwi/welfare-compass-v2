import Image from "next/image";
import { notFound } from "next/navigation";

import { BackButton } from "@/components/common/BackButton";
import { EDUCATION_CODE_MAP, JOB_CODE_MAP } from "@/constants/policy-codes";
import { ScrapButton } from "@/features/policy/ScrapButton";
import { fetchPolicyDetailById } from "@/features/policy/policy.api";
import { toPolicyCategoryFromName } from "@/features/policy/policy.constants";
import { POLICY_CATEGORY_IMAGE } from "@/features/policy/policy.images";

function cleanDisplayText(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/[○●•▪◦□ㅁ]/g, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatDate(date: string | null): string {
  if (!date) return "-";
  const normalized = date.slice(0, 10);
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return date;
  return `${parsed.getFullYear()}.${String(parsed.getMonth() + 1).padStart(2, "0")}.${String(parsed.getDate()).padStart(2, "0")}`;
}

export default async function PolicyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const policy = await fetchPolicyDetailById(id);

  if (!policy) notFound();

  const fallbackPoster = POLICY_CATEGORY_IMAGE[toPolicyCategoryFromName(policy.categories?.[0]?.name)];

  const cleanDescription = cleanDisplayText(policy.description);
  const cleanSupportContent = cleanDisplayText(policy.supportContent);
  const cleanApplyMethod = cleanDisplayText(policy.applyMethod);

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

  const ageRange = policy.minAge || policy.maxAge ? `${policy.minAge ?? ""}세 ~ ${policy.maxAge ?? ""}세` : "제한없음";

  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
      <section className="mx-auto w-full max-w-[980px]">
        <BackButton className="mb-4" />

        <div className="mb-3 flex items-center gap-2">
          {policy.categories.map((cat) => (
            <span key={cat.id} className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
              {cat.name}
            </span>
          ))}
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">{policy.region}</span>
        </div>

        <div className="mb-4 flex items-start justify-between gap-4 border-b border-gray-500 pb-3">
          <h1 className="text-2xl font-bold text-gray-900 md:text-3xl">{policy.title}</h1>
          <ScrapButton policyId={policy.id} className="mt-1" />
        </div>

        <div className="mb-8 flex w-full flex-col gap-8 overflow-hidden border-b border-gray-500 bg-white pb-1 md:flex-row lg:gap-25">
          {policy.posterUrl ? (
            <div className="ml-15 flex w-full flex-shrink-0 items-center justify-center rounded-xl bg-gray-50/50 p-6 md:w-[320px]">
              <div className="relative w-[280px]">
                <Image
                  src={policy.posterUrl}
                  alt={`${policy.title} 포스터`}
                  width={280}
                  height={396}
                  unoptimized
                  className="h-auto w-full rounded-lg object-contain shadow-sm"
                />
              </div>
            </div>
          ) : (
            <div className="ml-15 flex w-full flex-shrink-0 items-center justify-center rounded-xl bg-gray-50/50 p-6 md:w-[320px]">
              <div className="relative w-[280px]">
                <Image
                  src={fallbackPoster}
                  alt={`${policy.title} 기본 포스터`}
                  width={280}
                  height={396}
                  className="h-auto w-full rounded-lg object-contain shadow-sm"
                />
              </div>
            </div>
          )}

          <div className="flex flex-1 flex-col space-y-6 p-6">
            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-900">신청 정보</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">신청 기간</dt>
                  <dd className="font-medium text-gray-900">{applyPeriod}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">사업 기간</dt>
                  <dd className="text-gray-900">{bizPeriod}</dd>
                </div>
              </dl>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-900">자격 조건</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">연령</dt>
                  <dd className="text-gray-900">{ageRange}</dd>
                </div>

                {((policy.minIncome || 0) > 0 || (policy.maxIncome || 0) > 0) && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">소득 범위</dt>
                    <dd className="text-gray-900">
                      {policy.minIncome?.toLocaleString() ?? "0"}만원 ~ {policy.maxIncome?.toLocaleString() ?? "-"}만원
                    </dd>
                  </div>
                )}

                {policy.jobCode && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">직업 조건</dt>
                    <dd className="text-gray-900">
                      {String(policy.jobCode)
                        .split(",")
                        .map((c) => JOB_CODE_MAP[c.trim()] || c.trim())
                        .join(", ")}
                    </dd>
                  </div>
                )}

                {policy.schoolCode && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">학력 조건</dt>
                    <dd className="text-gray-900">
                      {String(policy.schoolCode)
                        .split(",")
                        .map((c) => EDUCATION_CODE_MAP[c.trim()] || c.trim())
                        .join(", ")}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-900">정책 정보</h3>
              <dl className="space-y-2 text-xs text-gray-500">
                <div className="flex justify-between">
                  <dt>해당지역</dt>
                  <dd className="text-gray-900">{policy.region}</dd>
                </div>
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

            <div className="mb-1 mt-auto">
              {policy.applyUrl && (
                <a
                  href={policy.applyUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full rounded-lg bg-blue-900 py-3 text-center text-sm font-medium text-white transition hover:bg-blue-950"
                >
                  신청하기 →
                </a>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-[980px] space-y-6">
        <div className="py-4">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">정책 설명</h2>
          <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700">{cleanDescription || "정책 설명이 없습니다."}</p>
        </div>

        {policy.supportContent && (
          <div className="pb-4">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">지원 내용</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700">{cleanSupportContent}</p>
          </div>
        )}

        {policy.applyMethod && (
          <div className="pb-4">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">신청 방법</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700">{cleanApplyMethod}</p>
          </div>
        )}
      </section>
    </div>
  );
}
