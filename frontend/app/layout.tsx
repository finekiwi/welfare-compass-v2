import "./globals.css";
import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ChatbotModalHost } from "@/features/chatbot/ChatbotModalHost";
import { ChatbotFloatingButton } from "@/features/chatbot/ChatbotFloatingButton";
import { FontSizeManager } from "@/components/common/FontSizeManager";
import { Providers } from "@/components/providers/Providers";

export const metadata: Metadata = {
    title: "복지나침반",
    description: "서울 청년 복지정책 추천 서비스",
    icons: {
        icon: "/favicon.ico"
    }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    // ✅ layout은 공통 UI(헤더/푸터) + 전역 오버레이 호스트(챗봇 모달)를 품습니다.
    // 이렇게 하면 어느 페이지에서도 챗봇 모달을 띄울 수 있어요.
    return (
        <html lang="ko">
            <head>
                <link rel="stylesheet" as="style" crossOrigin="anonymous" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css" />
            </head>
            <body className="antialiased">
                <Providers>
                    <Header />
                    <main className="min-h-[calc(100vh-160px)]">{children}</main>
                    <Footer />
                    <ChatbotModalHost />
                    <ChatbotFloatingButton />
                    <FontSizeManager />
                </Providers>
            </body>
        </html>
    );
}
