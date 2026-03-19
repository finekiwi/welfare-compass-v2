import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { TERMS_OF_SERVICE } from "@/features/auth/terms/termsData";

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">이용약관</h1>
      <article className="prose prose-sm max-w-none text-gray-700 md:prose-base">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{TERMS_OF_SERVICE}</ReactMarkdown>
      </article>
    </main>
  );
}
