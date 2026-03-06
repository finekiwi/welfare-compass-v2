"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/services/axios";
import { setVerified, getMyProfile } from "./mypage.api";

export function VerifyGate() {
    const router = useRouter();
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(true);
    const [hasPassword, setHasPassword] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                const profile = await getMyProfile();
                if (mounted) setHasPassword(profile.hasPassword ?? true);
            } catch (err) {
                console.error(err);
            } finally {
                if (mounted) setLoading(false);
            }
        })();
        return () => { mounted = false; };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSubmitting(true);

        try {
            const res = await api.post("/api/accounts/verify-password/", { password });
            const token = res.data.reauth_token;
            await setVerified(token);
            router.replace("/mypage/secure");
        } catch (err: any) {
            setError(err.response?.data?.error || "비밀번호 검증에 실패했습니다.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleSocialAuth = async () => {
        try {
            setSubmitting(true);
            const res = await api.post("/api/accounts/verify-social/");
            const token = res.data.reauth_token;
            await setVerified(token);
            router.replace("/mypage/secure");
        } catch (err: any) {
            console.error("소셜 재인증 오류:", err);
            setError(err.response?.data?.error || "소셜 계정 인증에 실패했습니다.");
            setSubmitting(false);
        }
    };

    if (loading) return <div className="p-10 text-center">확인 중...</div>;

    if (!hasPassword) {
        return (
            <div className="mx-auto max-w-md space-y-6 pt-10">
                <h1 className="text-2xl font-bold">본인 확인</h1>
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <p className="mb-6 text-sm text-gray-600">
                        소셜 로그인 계정입니다. 개인정보 보호를 위해 재인증(확인)을 진행합니다.
                    </p>
                    {error && <p className="mb-4 text-sm text-red-500">{error}</p>}
                    <button
                        onClick={handleSocialAuth}
                        disabled={submitting}
                        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {submitting ? "인증 처리 중..." : "인증하고 접근하기"}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-md space-y-6 pt-10">
            <h1 className="text-2xl font-bold">본인 확인</h1>
            <p className="text-sm text-gray-500">개인정보 보호를 위해 비밀번호를 다시 입력해주세요.</p>

            <form onSubmit={handleSubmit} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="mb-4">
                    <label className="mb-2 block text-sm font-medium text-gray-900">비밀번호</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="비밀번호 입력"
                        required
                    />
                </div>

                {error && <p className="mb-4 text-sm text-red-500">{error}</p>}

                <button
                    type="submit"
                    disabled={submitting}
                    className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                    {submitting ? "확인 중..." : "확인"}
                </button>
            </form>
        </div>
    );
}
