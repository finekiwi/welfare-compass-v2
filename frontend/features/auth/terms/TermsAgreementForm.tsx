// features/auth/terms/TermsAgreementForm.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { TERMS_OF_SERVICE, PRIVACY_POLICY } from "./termsData";

type TermsModalType = "terms" | "privacy" | null;

export function TermsAgreementForm() {
    const router = useRouter();

    // 동의 상태
    const [agreeAll, setAgreeAll] = useState(false);
    const [agreeTerms, setAgreeTerms] = useState(false);
    const [agreePrivacy, setAgreePrivacy] = useState(false);
    const [agreeMarketing, setAgreeMarketing] = useState(false);

    // 모달 상태
    const [showModal, setShowModal] = useState<TermsModalType>(null);

    // 전체 동의 핸들러
    const handleAgreeAll = (checked: boolean) => {
        setAgreeAll(checked);
        setAgreeTerms(checked);
        setAgreePrivacy(checked);
        setAgreeMarketing(checked);
    };

    // 개별 동의 변경 시 전체 동의 상태 업데이트
    const updateAgreeAll = (terms: boolean, privacy: boolean, marketing: boolean) => {
        setAgreeAll(terms && privacy && marketing);
    };

    // 필수 항목 확인
    const canProceed = agreeTerms && agreePrivacy;

    // 다음 단계로 이동
    const handleNext = () => {
        if (!canProceed) {
            alert("필수 약관에 동의해주세요.");
            return;
        }

        // 마케팅 동의 여부를 쿼리 파라미터로 전달
        router.push(`/signup/form?marketing=${agreeMarketing}`);
    };

    return (
        <div className="mx-auto w-full max-w-lg space-y-6 rounded-xl border p-6">
            <div>
                <h1 className="text-xl font-bold">약관동의</h1>
                <p className="text-sm text-gray-500 mt-1">
                    복지나침반 서비스 이용을 위해 약관에 동의해주세요.
                </p>
            </div>

            {/* 전체 동의 */}
            <div className="rounded-lg bg-gray-50 p-4">
                <label className="flex items-center gap-3 cursor-pointer">
                    <input
                        type="checkbox"
                        className="h-5 w-5 rounded border-gray-300 accent-blue-600"
                        checked={agreeAll}
                        onChange={(e) => handleAgreeAll(e.target.checked)}
                    />
                    <span className="font-semibold">전체 동의하기</span>
                </label>
                <p className="text-xs text-gray-500 mt-2 ml-8">
                    서비스 이용약관, 개인정보 수집 및 이용, 마케팅 수신(선택)에 모두 동의합니다.
                </p>
            </div>

            <div className="h-px bg-gray-200" />

            {/* 개별 동의 항목 */}
            <div className="space-y-4">
                {/* 이용약관 */}
                <div className="flex items-center justify-between">
                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-5 w-5 rounded border-gray-300 accent-blue-600"
                            checked={agreeTerms}
                            onChange={(e) => {
                                setAgreeTerms(e.target.checked);
                                updateAgreeAll(e.target.checked, agreePrivacy, agreeMarketing);
                            }}
                        />
                        <span className="text-sm">
                            <span className="text-red-500 font-medium">(필수)</span> 복지나침반 이용약관
                        </span>
                    </label>
                    <button
                        type="button"
                        onClick={() => setShowModal("terms")}
                        className="text-xs text-gray-500 underline hover:text-gray-700"
                    >
                        전문보기
                    </button>
                </div>

                {/* 개인정보 수집 및 이용 */}
                <div className="flex items-center justify-between">
                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-5 w-5 rounded border-gray-300 accent-blue-600"
                            checked={agreePrivacy}
                            onChange={(e) => {
                                setAgreePrivacy(e.target.checked);
                                updateAgreeAll(agreeTerms, e.target.checked, agreeMarketing);
                            }}
                        />
                        <span className="text-sm">
                            <span className="text-red-500 font-medium">(필수)</span> 개인정보 수집 및 이용 동의
                        </span>
                    </label>
                    <button
                        type="button"
                        onClick={() => setShowModal("privacy")}
                        className="text-xs text-gray-500 underline hover:text-gray-700"
                    >
                        전문보기
                    </button>
                </div>

                {/* 마케팅 수신 동의 */}
                <div className="flex items-center justify-between">
                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-5 w-5 rounded border-gray-300 accent-blue-600"
                            checked={agreeMarketing}
                            onChange={(e) => {
                                setAgreeMarketing(e.target.checked);
                                updateAgreeAll(agreeTerms, agreePrivacy, e.target.checked);
                            }}
                        />
                        <span className="text-sm">
                            <span className="text-gray-400 font-medium">(선택)</span> 정책정보 알림 수신 동의
                        </span>
                    </label>
                </div>
            </div>

            {/* 안내 문구 */}
            <div className="rounded-lg bg-blue-50 p-3 text-xs text-gray-600">
                <p>※ 필수 약관에 동의하지 않으시면 서비스 이용이 제한됩니다.</p>
                <p>※ 선택 항목은 동의하지 않아도 회원가입이 가능합니다.</p>
            </div>

            {/* 다음 버튼 */}
            <button
                type="button"
                onClick={handleNext}
                disabled={!canProceed}
                className="w-full rounded-lg bg-black py-3 text-sm font-semibold text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 transition"
            >
                다음
            </button>

            <p className="text-xs text-gray-500 text-center">
                이미 계정이 있나요? <a className="underline" href="/login">로그인</a>
            </p>

            {/* 약관 모달 */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="w-full max-w-2xl max-h-[80vh] rounded-2xl bg-white shadow-xl flex flex-col">
                        <div className="flex items-center justify-between border-b p-4">
                            <h2 className="text-lg font-bold">
                                {showModal === "terms" ? "복지나침반 이용약관" : "개인정보 수집 및 이용 동의"}
                            </h2>
                            <button
                                type="button"
                                onClick={() => setShowModal(null)}
                                className="text-gray-500 hover:text-gray-700 text-xl"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-6">
                            <article className="prose prose-sm max-w-none text-gray-700">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {showModal === "terms" ? TERMS_OF_SERVICE : PRIVACY_POLICY}
                                </ReactMarkdown>
                            </article>
                        </div>
                        <div className="border-t p-4">
                            <button
                                type="button"
                                onClick={() => setShowModal(null)}
                                className="w-full rounded-lg bg-gray-900 py-2 text-sm font-medium text-white hover:bg-gray-800"
                            >
                                확인
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
