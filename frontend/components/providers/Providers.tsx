"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";

/**
 * 전역 Provider 컴포넌트
 * - Google OAuth Provider 등 클라이언트 사이드 설정이 필요한 Provider들을 여기서 관리합니다.
 */
export function Providers({ children }: { children: React.ReactNode }) {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

    if (!clientId) {
        console.warn("⚠️ Google Client ID가 설정되지 않았습니다.");
    }

    return (
        <GoogleOAuthProvider clientId={clientId}>
            {children}
        </GoogleOAuthProvider>
    );
}
