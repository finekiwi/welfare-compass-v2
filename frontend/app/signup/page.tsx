// app/signup/page.tsx
import { SignupForm } from "@/features/auth/SignupForm";

export default function SignupPage() {
  return (
    <main className="px-4 py-10">
      <SignupForm />
    </main>
  );
}
