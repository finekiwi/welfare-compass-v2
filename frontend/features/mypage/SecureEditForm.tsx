// features/mypage/SecureEditForm.tsx

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearVerified, getMyProfile, getVerifyState, saveMyProfile } from "./mypage.api";
import type { MyProfile } from "./mypage.types";

export function SecureEditForm() {
    const router = useRouter();
    const [verified, setVerifiedState] = useState<boolean | null>(null);
    const [form, setForm] = useState<MyProfile | null>(null);

    // 비밀번호는 목업이라 실제 저장 X (UI만)
    const [currentPw, setCurrentPw] = useState("");
    const [newPw, setNewPw] = useState("");
    const [newPw2, setNewPw2] = useState("");

    useEffect(() => {
        (async () => {
            const v = await getVerifyState();
            if (!v.isVerified) {
                setVerifiedState(false);
                router.replace("/mypage/verify");
                return;
            }
            setVerifiedState(true);
            setForm(await getMyProfile());
        })();
    }, [router]);

    if (verified === null) {
        return <div className="rounded-2xl border bg-white p-6 text-sm text-gray-600">확인 중...</div>;
    }

    // replace로 보내서 여기 도착하면 거의 verified=true 상태
    if (!form) return null;

    async function onSave() {
        if (!form) return; // ✅ null이면 저장하지 않음(가드)
        await saveMyProfile(form);
        // 인증은 보통 “일회성”으로 처리하는 경우가 많아서 저장 후 해제
        await clearVerified();
        router.push("/mypage");
    }

    return (
        <div className="space-y-6">
            <div className="text-sm text-gray-500">홈 &gt; 마이페이지 &gt; 나의정보관리 &gt; 내 정보 수정하기</div>
            <h1 className="text-3xl font-bold">내 정보 수정하기</h1>

            <div className="rounded-2xl bg-gray-50 p-5 text-sm text-gray-600">
                <ul className="list-disc space-y-1 pl-5">
                    <li>중요 개인정보는 신중히 취급하며, 인증 이후에만 변경 가능합니다.</li>
                    <li>현재는 목업 화면으로 저장 시 로컬에만 반영됩니다.</li>
                </ul>
            </div>

            {/* 개인정보 */}
            <section className="rounded-2xl border bg-white p-6">
                <div className="mb-4 text-lg font-bold">개인회원정보</div>

                <div className="grid gap-4 md:grid-cols-2">
                    <label className="block">
                        <div className="mb-1 text-xs text-gray-600">성명</div>
                        <div className="flex gap-2">
                            <input
                                value={form.displayName}
                                onChange={(e) => setForm({ ...form, displayName: e.target.value })}
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                            <button type="button" className="h-11 rounded-lg bg-gray-900 px-3 text-xs font-semibold text-white">
                                성명 변경하기
                            </button>
                        </div>
                    </label>

                    <label className="block">
                        <div className="mb-1 text-xs text-gray-600">휴대전화번호</div>
                        <div className="flex gap-2">
                            <input
                                value={form.phone}
                                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                            <button type="button" className="h-11 rounded-lg bg-gray-900 px-3 text-xs font-semibold text-white">
                                휴대전화번호 변경하기
                            </button>
                        </div>
                    </label>

                    <label className="block md:col-span-2">
                        <div className="mb-1 text-xs text-gray-600">이메일</div>
                        <div className="flex gap-2">
                            <input
                                value={form.email}
                                onChange={(e) => setForm({ ...form, email: e.target.value })}
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                        </div>
                    </label>
                </div>
            </section>

            {/* 비밀번호 재설정 */}
            <section className="rounded-2xl border bg-white p-6">
                <div className="mb-4 text-lg font-bold">비밀번호 재설정</div>

                <div className="grid gap-4 md:grid-cols-2">
                    <label className="block md:col-span-2">
                        <div className="mb-1 text-xs text-gray-600">기존 비밀번호</div>
                        <input
                            type="password"
                            value={currentPw}
                            onChange={(e) => setCurrentPw(e.target.value)}
                            className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                        />
                        <div className="mt-1 text-[11px] text-gray-500">
                            영문(대/소문자), 숫자, 특수문자 중 3가지 이상 조합하여 9~24자 이내
                        </div>
                    </label>

                    <label className="block">
                        <div className="mb-1 text-xs text-gray-600">새 비밀번호</div>
                        <input
                            type="password"
                            value={newPw}
                            onChange={(e) => setNewPw(e.target.value)}
                            className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                        />
                    </label>

                    <label className="block">
                        <div className="mb-1 text-xs text-gray-600">새 비밀번호 확인</div>
                        <input
                            type="password"
                            value={newPw2}
                            onChange={(e) => setNewPw2(e.target.value)}
                            className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                        />
                        {newPw && newPw2 && newPw !== newPw2 ? (
                            <div className="mt-1 text-[11px] text-red-500">비밀번호가 일치하지 않습니다.</div>
                        ) : null}
                    </label>
                </div>
            </section>

            {/* 하단 버튼 */}
            <div className="flex items-center justify-between">
                <Link href="/mypage" className="rounded-lg border px-4 py-2 text-sm">
                    이전으로
                </Link>

                <button
                    type="button"
                    onClick={onSave}
                    className="rounded-lg bg-blue-800 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                >
                    수정하기
                </button>
            </div>
        </div>
    );
}
