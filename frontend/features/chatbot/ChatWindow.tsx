// features/chatbot/ChatWindow.tsx
"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { useChatbotStore } from "@/stores/chatbot.store";
import { useAuthStore } from "@/stores/auth.store";
import { useProfileStore } from "@/stores/profile.store";
import { ChatMessageBubble } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

// 취업상태 라벨 매핑
const JOB_STATUS_LABELS: Record<string, string> = {
  employed: "재직중",
  unemployed: "미취업",
  job_seeking: "구직중",
  student: "학생",
  startup: "창업준비",
  freelancer: "프리랜서",
  other: "기타",
};

export function ChatWindow() {
  const messages = useChatbotStore((s) => s.messages);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const profile = useProfileStore((s) => s.profile);
  const fetchProfile = useProfileStore((s) => s.fetchProfile);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 로그인 상태일 때만 프로필 불러오기
  useEffect(() => {
    if (isAuthenticated && !profile) {
      fetchProfile();
    }
  }, [isAuthenticated, profile, fetchProfile]);

  // 새 메시지마다 하단으로 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 소득 표시 포맷팅
  const formatIncome = () => {
    if (!profile) return "-";
    if (profile.incomeAmount != null) {
      return `월 ${profile.incomeAmount}만원`;
    }
    return "-";
  };

  // 나이 계산
  const getAge = () => {
    if (!profile || !profile.birthYear) return null;
    return new Date().getFullYear() - profile.birthYear;
  };

  return (
    <div className={`grid grid-cols-1 gap-4 p-5 ${isAuthenticated ? "md:grid-cols-[320px_1fr]" : ""}`}>
      {/* 왼쪽: 사용자 정보 요약 (로그인 시에만 표시) */}
      {isAuthenticated && <aside className="rounded-xl border bg-gray-50 p-4">
        <div className="text-sm font-semibold">내 정보 요약</div>
        <div className="mt-3 space-y-2 text-xs text-gray-700">
          <Row
            label="나이"
            value={getAge() != null ? `만 ${getAge()}세` : "-"}
          />
          <Row
            label="거주지"
            value={profile?.district || "-"}
          />
          <Row
            label="구직/재직"
            value={profile?.jobStatus ? JOB_STATUS_LABELS[profile.jobStatus] || "-" : "-"}
          />
          <Row
            label="소득"
            value={formatIncome()}
          />
        </div>

        <Link href="/mypage/profile">
          <button className="mt-4 w-full rounded-xl border bg-white px-3 py-2 text-xs hover:bg-gray-100 transition">
            내정보 업데이트
          </button>
        </Link>
      </aside>}

      {/* 오른쪽: 채팅 */}
      <section className="flex h-[520px] flex-col rounded-xl border">
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="border-t p-3">
          <ChatInput />
        </div>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-white px-3 py-2">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
