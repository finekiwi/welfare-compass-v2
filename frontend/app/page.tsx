// app/page.tsx
import { CategoryMenu } from "@/features/home/CategoryMenu";
import { HomeLoginChatSection } from "@/features/home/HomeLoginChatSection";
import { YouthPolicySection } from "@/features/policy/YouthPolicySection";

export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-[1320px] px-4 py-4">
      <CategoryMenu />

      <div className="my-6 lg:my-8">
        <HomeLoginChatSection />
      </div>

      <YouthPolicySection />
    </div>
  );
}
