// app/signup/form/page.tsx
import { Suspense } from "react";
import { SignupForm } from "@/features/auth/SignupForm";

export default function SignupFormPage() {
    return (
        <main className="px-4 py-10">
            <Suspense fallback={<div>로딩중...</div>}>
                <SignupForm />
            </Suspense>
        </main>
    );
}
