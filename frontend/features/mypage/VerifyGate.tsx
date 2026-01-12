// features/mypage/VerifyGate.tsx

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { setVerified } from "./mypage.api";

export function VerifyGate() {
    const router = useRouter();

    async function onVerify() {
        await setVerified();
        router.push("/mypage/secure");
    }

    return (
        <div className="space-y-6">
            <div className="text-sm text-gray-500">홈 &gt; 마이페이지 &gt; 나의정보관리 &gt; 내 정보 수정하기</div>
            <h1 className="text-3xl font-bold">내 정보 수정하기</h1>

            <div className="rounded-2xl bg-gray-50 p-5 text-sm text-gray-600">
                <ul className="list-disc space-y-1 pl-5">
                    <li>중요 개인정보는 본인 인증 후 수정할 수 있습니다.</li>
                    <li>회원정보 보호를 위해 인증 절차를 진행합니다.</li>
                </ul>
            </div>

            <div className="rounded-2xl border bg-white p-6">
                <div className="mb-4 text-lg font-bold">본인 인증하기</div>

                <button
                    type="button"
                    onClick={onVerify}
                    className="flex w-full items-center justify-between rounded-xl border p-5 hover:bg-gray-50"
                >
                    <div className="flex items-center gap-3">
                        <div className="grid h-10 w-10 place-items-center rounded-lg bg-gray-100">👤</div>
                        <div className="text-left">
                            <div className="font-semibold">휴대폰 인증</div>
                            <div className="text-sm text-gray-500">본인 휴대폰정보 인증 후 수정하실 수 있습니다.</div>
                        </div>
                    </div>
                    <span className="text-gray-400">›</span>
                </button>
            </div>

            <Link href="/mypage" className="inline-block text-sm text-gray-600 hover:underline">
                마이페이지로 돌아가기
            </Link>
        </div>
    );
}
