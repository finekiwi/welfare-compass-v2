// app/page.tsx
import { HeroBanner } from "@/features/home/HeroBanner";
import { CategoryMenu } from "@/features/home/CategoryMenu";
import { PriorityPolicyList } from "@/features/policy/PriorityPolicyList";
import { ChatbotLauncher } from "@/features/chatbot/ChatbotLauncher";
import { YouthPolicySection } from "@/features/policy/YouthPolicySection";

export default function HomePage() {
  // ✅ 메인 페이지는 "조립"만 담당(로직 최소화)
  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
      <HeroBanner />
      <CategoryMenu />
      <PriorityPolicyList />

      {/* ✅ ② 이미지처럼 메인 중간에 챗봇 런처 섹션 */}
      <div className="my-10">
        <ChatbotLauncher />
      </div>

      <YouthPolicySection />
    </div>
  );
}
