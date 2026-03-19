import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { PRIVACY_POLICY } from "@/features/auth/terms/termsData";

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">개인정보처리방침</h1>
      <article className="prose prose-sm max-w-none text-gray-700 md:prose-base">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{PRIVACY_POLICY}</ReactMarkdown>
      </article>
    </main>
  );
}
