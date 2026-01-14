// app/mypage/layout.tsx
import type { ReactNode } from "react";
import { MyPageShell } from "@/features/mypage/MyPageShell";

export default function MyPageLayout({ children }: { children: ReactNode }) {
    // ✅ mypage 이하 모든 라우트(/mypage, /mypage/profile, /mypage/secure, /mypage/verify)가
    //    동일한 왼쪽 메뉴 + 오른쪽 본문 레이아웃을 공유하게 됨
    return <MyPageShell>{children}</MyPageShell>;
}