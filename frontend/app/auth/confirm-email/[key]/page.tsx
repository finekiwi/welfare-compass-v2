"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { verifyEmail } from "@/features/auth/auth.api";
import Link from "next/link";
import { useParams } from "next/navigation"; // App Router

export default function ConfirmEmailPage() {
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const params = useParams();
    const key = params?.key as string;

    useEffect(() => {
        if (!key) {
            setStatus('error');
            return;
        }

        const verify = async () => {
            try {
                // 키 정제 (URL 디코딩 및 공백/슬래시 제거)
                let cleanKey = decodeURIComponent(key).trim();
                if (cleanKey.endsWith('/')) {
                    cleanKey = cleanKey.slice(0, -1);
                }

                await verifyEmail(cleanKey);
                setStatus('success');
            } catch (error) {
                console.error("Email verification failed:", error);
                setStatus('error');
            }
        };
        verify();
    }, [key]);

    return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-4">
            <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm">
                <h1 className="mb-6 text-center text-2xl font-bold">이메일 인증</h1>

                {status === 'loading' && (
                    <div className="text-center">
                        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600 mx-auto"></div>
                        <p className="text-gray-600">인증을 진행하고 있습니다...</p>
                    </div>
                )}

                {status === 'success' && (
                    <div className="text-center">
                        <div className="mb-4 text-5xl text-green-500">✅</div>
                        <h2 className="mb-2 text-xl font-semibold text-gray-800">인증이 완료되었습니다!</h2>
                        <p className="mb-6 text-gray-600">이제 모든 서비스를 이용하실 수 있습니다.</p>
                        <Link
                            href="/login"
                            className="inline-block w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors"
                        >
                            로그인하러 가기
                        </Link>
                    </div>
                )}

                {status === 'error' && (
                    <div className="text-center">
                        <div className="mb-4 text-5xl text-red-500">⚠️</div>
                        <h2 className="mb-2 text-xl font-semibold text-gray-800">인증에 실패했습니다.</h2>
                        <p className="mb-4 text-gray-600">유효하지 않거나 이미 만료된 링크입니다.</p>
                        <Link
                            href="/"
                            className="text-sm text-blue-600 hover:text-blue-800 underline"
                        >
                            홈으로 돌아가기
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}
