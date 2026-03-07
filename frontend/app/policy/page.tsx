// app/policy/page.tsx
import { Suspense } from "react";
import { PolicySearchPageClient } from "@/features/policy/PolicySearchPageClient";

export default function PolicyPage() {
    return (
        <Suspense fallback={<div>로딩중...</div>}>
            <PolicySearchPageClient />
        </Suspense>
    );
}
