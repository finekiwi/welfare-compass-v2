"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { confirmPasswordReset } from "@/features/auth/auth.api";
import Link from "next/link";

export default function PasswordResetConfirmPage() {
    const params = useParams();
    const uid = params?.uid as string;
    const token = params?.token as string;
    const router = useRouter();

    const [password, setPassword] = useState("");
    const [password2, setPassword2] = useState("");
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState("");

    // ✅ 비밀번호 유효성 검사 함수 (SignupForm과 동일)
    const validatePassword = (pw: string) => {
        const hasLetter = /[a-zA-Z]/.test(pw);
        const hasNumber = /[0-9]/.test(pw);
        const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw);
        const isLongEnough = pw.length >= 8;

        return {
            hasLetter,
            hasNumber,
            hasSpecial,
            isLongEnough,
            isValid: hasLetter && hasNumber && hasSpecial && isLongEnough,
        };
    };

    const passwordValidation = validatePassword(password);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== password2) {
            setMessage("비밀번호가 일치하지 않습니다.");
            return;
        }

        if (!passwordValidation.isValid) {
            setMessage("영문, 숫자, 특수문자를 모두 포함하여 8자 이상 입력해주세요.");
            return;
        }

        setLoading(true);
        setStatus('idle');
        setMessage("");

        try {
            await confirmPasswordReset({
                uid,
                token,
                new_password1: password,
                new_password2: password2,
            });
            setStatus('success');
        } catch (error: any) {
            console.error(error);
            setStatus('error');
            setMessage("비밀번호 재설정에 실패했습니다. 유효하지 않거나 만료된 링크일 수 있습니다.");
        } finally {
            setLoading(false);
        }
    };

    if (status === 'success') {
        return (
            <div className="flex min-h-[400px] flex-col items-center justify-center p-4">
                <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm text-center">
                    <div className="mb-4 text-5xl text-green-500">✅</div>
                    <h2 className="mb-2 text-xl font-semibold text-gray-800">비밀번호 변경 완료</h2>
                    <p className="mb-6 text-gray-600">새로운 비밀번호로 로그인해주세요.</p>
                    <Link
                        href="/login"
                        className="inline-block w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors"
                    >
                        로그인하러 가기
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-[500px] flex-col items-center justify-center p-4">
            <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm">
                <h1 className="mb-6 text-center text-2xl font-bold">비밀번호 재설정</h1>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <label className="mb-1 block text-sm font-medium text-gray-700">새 비밀번호</label>
                        <input
                            type="password"
                            required
                            className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                            placeholder="8자 이상 입력"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        {/* ✅ 실시간 비밀번호 유효성 검사 (한 줄로 표시) */}
                        {password.length > 0 && (
                            <div className="flex flex-wrap gap-3 text-[11px]">
                                <span className={passwordValidation.isLongEnough ? "text-green-600" : "text-red-500"}>
                                    {passwordValidation.isLongEnough ? "✓" : "○"} 8자 이상
                                </span>
                                <span className={passwordValidation.hasLetter ? "text-green-600" : "text-red-500"}>
                                    {passwordValidation.hasLetter ? "✓" : "○"} 영문
                                </span>
                                <span className={passwordValidation.hasNumber ? "text-green-600" : "text-red-500"}>
                                    {passwordValidation.hasNumber ? "✓" : "○"} 숫자
                                </span>
                                <span className={passwordValidation.hasSpecial ? "text-green-600" : "text-red-500"}>
                                    {passwordValidation.hasSpecial ? "✓" : "○"} 특수문자
                                </span>
                            </div>
                        )}
                        {password.length === 0 && (
                            <p className="text-[11px] text-gray-600">
                                * 영문, 숫자, 특수문자를 모두 포함하여 8자 이상 입력해주세요.
                            </p>
                        )}
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-gray-700">새 비밀번호 확인</label>
                        <input
                            type="password"
                            required
                            className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                            placeholder="비밀번호 다시 입력"
                            value={password2}
                            onChange={(e) => setPassword2(e.target.value)}
                        />
                        {/* ✅ 비밀번호 일치/불일치 표시 */}
                        {password && password2 && (
                            password === password2 ? (
                                <p className="text-[11px] text-green-600 font-medium">✓ 비밀번호가 일치합니다.</p>
                            ) : (
                                <p className="text-[11px] text-red-500 font-medium">❌ 비밀번호가 일치하지 않습니다.</p>
                            )
                        )}
                    </div>

                    {message && (
                        <div className="rounded bg-red-50 p-3 text-sm text-red-700 text-center">
                            {message}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading || !passwordValidation.isValid || password !== password2}
                        className="w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
                    >
                        {loading ? "변경 중..." : "비밀번호 변경하기"}
                    </button>
                </form>
            </div>
        </div>
    );
}
