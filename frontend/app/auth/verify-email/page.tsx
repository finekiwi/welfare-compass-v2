"use client";

import Link from "next/link";

export default function VerifyEmailInfoPage() {
    return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-4">
            <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm text-center">
                <div className="mb-4 text-5xl">📧</div>
                <h1 className="mb-2 text-2xl font-bold text-gray-800">이메일을 확인해주세요</h1>
                <p className="mb-6 text-gray-600">
                    회원가입 시 입력하신 이메일로<br />
                    인증 링크를 발송했습니다.
                </p>
                <div className="mb-6 rounded bg-blue-50 p-4 text-sm text-blue-800">
                    <p>메일함에 이메일이 도착하지 않았다면?</p>
                    <ul className="mt-2 list-inside list-disc text-left">
                        <li>스팸 메일함을 확인해주세요.</li>
                        <li>입력하신 이메일 주소가 정확한지 확인해주세요.</li>
                    </ul>
                </div>
                <Link
                    href="/login"
                    className="inline-block w-full rounded-md bg-gray-600 px-4 py-2 text-white hover:bg-gray-700 transition-colors"
                >
                    로그인 페이지로 이동
                </Link>
            </div>
        </div>
    );
}
