"use client";

import { useState, useRef } from "react";
import { findUsername, requestPasswordReset } from "@/features/auth/auth.api";
import Link from "next/link";
import ReCAPTCHA from "react-google-recaptcha";

type Tab = 'id' | 'password';

export default function FindAccountPage() {
    const [activeTab, setActiveTab] = useState<Tab>('id');
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const recaptchaRef = useRef<ReCAPTCHA>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // [보안] 운영 환경에서만 reCAPTCHA 필수, 개발 환경에서는 키 없어도 테스트 가능
        const isProduction = process.env.NODE_ENV === 'production';
        if (isProduction && !process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY) {
            setMessage({ type: 'error', text: "reCAPTCHA 환경 변수가 설정되지 않아 진행할 수 없습니다." });
            return;
        }

        const token = recaptchaRef.current?.getValue();
        if (!token && isProduction) {
            setMessage({ type: 'error', text: "로봇이 아님을 증명해주세요." });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            if (activeTab === 'id') {
                await findUsername(email, token);
                setMessage({ type: 'success', text: "입력하신 이메일이 가입된 계정이라면, 아이디 정보를 발송했습니다." });
            } else {
                await requestPasswordReset(email, token);
                setMessage({ type: 'success', text: "입력하신 이메일이 가입된 계정이라면, 비밀번호 재설정 링크를 발송했습니다." });
            }
            recaptchaRef.current?.reset();
        } catch (error: any) {
            console.error(error);
            const errorMsg = error.response?.data?.error || "요청 처리에 실패했습니다. 잠시 후 다시 시도해주세요.";
            setMessage({ type: 'error', text: errorMsg });
            recaptchaRef.current?.reset();
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-[500px] flex-col items-center justify-center p-4">
            <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm">
                <h1 className="mb-6 text-center text-2xl font-bold">계정 찾기</h1>

                {/* 탭 버튼 */}
                <div className="mb-6 flex border-b">
                    <button
                        className={`flex-1 py-2 text-sm font-medium transition-colors ${activeTab === 'id'
                            ? "border-b-2 border-blue-600 text-blue-600"
                            : "text-gray-500 hover:text-gray-700"
                            }`}
                        onClick={() => { setActiveTab('id'); setMessage(null); }}
                    >
                        아이디 찾기
                    </button>
                    <button
                        className={`flex-1 py-2 text-sm font-medium transition-colors ${activeTab === 'password'
                            ? "border-b-2 border-blue-600 text-blue-600"
                            : "text-gray-500 hover:text-gray-700"
                            }`}
                        onClick={() => { setActiveTab('password'); setMessage(null); }}
                    >
                        비밀번호 찾기
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-gray-700">이메일</label>
                        <input
                            type="email"
                            required
                            className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                            placeholder="가입 시 등록한 이메일 입력"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    <div className="flex justify-center">
                        {process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY ? (
                            <ReCAPTCHA
                                ref={recaptchaRef}
                                sitekey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY}
                            />
                        ) : process.env.NODE_ENV === 'production' ? (
                            <div className="p-4 text-sm text-red-600 bg-red-50 rounded-md">
                                reCAPTCHA 환경 변수가 설정되지 않아 인증을 진행할 수 없습니다. 관리자에게 문의하세요.
                            </div>
                        ) : (
                            <div className="p-4 text-sm text-yellow-700 bg-yellow-50 rounded-md">
                                ⚠️ 개발 환경: reCAPTCHA 키가 설정되지 않아 캡챠 없이 테스트가 가능합니다.
                            </div>
                        )}
                    </div>

                    {message && (
                        <div className={`rounded p-3 text-sm ${message.type === 'success' ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                            }`}>
                            {message.text}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
                    >
                        {loading ? "처리 중..." : (activeTab === 'id' ? "아이디 찾기" : "비밀번호 재설정 메일 발송")}
                    </button>
                </form>

                <div className="mt-6 text-center text-xs text-gray-500">
                    <Link href="/login" className="hover:underline">로그인으로 돌아가기</Link>
                    <span className="mx-2">|</span>
                    <Link href="/signup" className="hover:underline">회원가입</Link>
                </div>
            </div>
        </div>
    );
}
