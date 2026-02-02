// app/signup/page.tsx
import { TermsAgreementForm } from "@/features/auth/terms/TermsAgreementForm";

export default function SignupPage() {
  return (
    <main className="px-4 py-10">
      <TermsAgreementForm />
    </main>
  );
}
