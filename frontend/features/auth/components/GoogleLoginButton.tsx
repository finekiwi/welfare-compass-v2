"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { loginWithGoogle } from "../auth.api";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth.store";

export default function GoogleLoginButton() {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

    // Client ID가 없으면 버튼 자체를 렌더링하지 않음 (Hook 실행 방지)
    if (!clientId) {
        return null; // 또는 대체 UI (예: "로그인 설정 필요")
    }

    return <GoogleLoginButtonContent />;
}

function GoogleLoginButtonContent() {
    const router = useRouter();
    const login = useAuthStore((state) => state.login);

    const handleGoogleLogin = useGoogleLogin({
        onSuccess: async ({ code }) => {
            try {
                console.log("Google Code:", code); // 디버깅용
                await loginWithGoogle(code);

                // 로그인 성공 시 상태 업데이트 (await 필수 — 쿠키 검증 후 이동)
                await login();

                // 메인 페이지로 이동
                router.push("/");
            } catch (error) {
                console.error("Google Login Failed:", error);
                const axiosError = error as any;
                console.error("Google Login Failed Data JSON:", JSON.stringify(axiosError?.response?.data));
                console.error("Google Login Failed Detail:", {
                    status: axiosError?.response?.status,
                    url: axiosError?.config?.url,
                    data: axiosError?.response?.data,
                });
                alert("구글 로그인에 실패했습니다.");
            }
        },
        onError: (errorResponse) => {
            console.error("Google Login Error:", errorResponse);
            alert("구글 로그인 중 오류가 발생했습니다.");
        },
        flow: "auth-code", // Authorization Code Flow 사용 (보안 권장)
    });

    return (
        <button
            onClick={() => handleGoogleLogin()}
            className="flex w-full items-center justify-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            type="button"
        >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    fill="#4285F4"
                />
                <path
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    fill="#34A853"
                />
                <path
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    fill="#FBBC05"
                />
                <path
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    fill="#EA4335"
                />
            </svg>
            Google로 시작하기
        </button>
    );
}
