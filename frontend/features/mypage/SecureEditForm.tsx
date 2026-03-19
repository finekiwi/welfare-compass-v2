// features/mypage/SecureEditForm.tsx

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getMyProfile, getVerifyState, saveMyProfile } from "./mypage.api";
import type { MyProfile } from "./mypage.types";
import { api } from "@/services/axios";

export function SecureEditForm() {
    const router = useRouter();
    const [verified, setVerifiedState] = useState<boolean | null>(null);
    const [reauthToken, setReauthToken] = useState<string | undefined>(undefined);
    const [form, setForm] = useState<MyProfile | null>(null);
    const [isSavingNotifications, setIsSavingNotifications] = useState(false);
    const [notificationMessage, setNotificationMessage] = useState<string | null>(null);

    // 비밀번호 변경
    const [newPw, setNewPw] = useState("");
    const [newPw2, setNewPw2] = useState("");
    const [pwError, setPwError] = useState("");
    const [pwSuccess, setPwSuccess] = useState("");
    const [isChangingPw, setIsChangingPw] = useState(false);

    // 회원탈퇴
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deletePw, setDeletePw] = useState("");
    const [deleteError, setDeleteError] = useState("");
    const [isDeleting, setIsDeleting] = useState(false);
    const newPwTooShort = newPw.length > 0 && newPw.length < 8;
    const newPwMismatch = newPw2.length > 0 && newPw !== newPw2;
    const newPwHasLetter = /[a-zA-Z]/.test(newPw);
    const newPwHasNumber = /[0-9]/.test(newPw);
    const newPwHasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newPw);
    const newPwRuleInvalid = newPw.length > 0 && (!newPwHasLetter || !newPwHasNumber || !newPwHasSpecial);

    const translatePasswordError = (message: string) => {
        const mappings: Array<[RegExp, string]> = [
            [/too common/i, "너무 흔한 비밀번호입니다."],
            [/too short/i, "비밀번호는 8자 이상이어야 합니다."],
            [/entirely numeric/i, "숫자로만 된 비밀번호는 사용할 수 없습니다."],
            [/too similar/i, "개인정보와 비슷한 비밀번호는 사용할 수 없습니다."],
        ];
        for (const [pattern, translated] of mappings) {
            if (pattern.test(message)) return translated;
        }
        return message;
    };

    useEffect(() => {
        (async () => {
            const state = await getVerifyState();
            if (!state.isVerified) {
                router.replace("/mypage/verify");
                return;
            }
            setVerifiedState(true);
            setReauthToken(state.reauthToken);
            setForm(await getMyProfile());
        })();
    }, [router]);

    if (verified === null) {
        return <div className="rounded-2xl border bg-white p-6 text-sm text-gray-600">확인 중...</div>;
    }

    if (!form) return null;

    async function handleSaveNotifications() {
        if (!form) {
            setNotificationMessage("프로필 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
            return;
        }
        if (!reauthToken) {
            setNotificationMessage("재인증 정보가 없습니다. 다시 인증해주세요.");
            return;
        }
        setIsSavingNotifications(true);
        setNotificationMessage(null);
        try {
            await saveMyProfile(form, reauthToken);
            setNotificationMessage("알림 설정이 저장되었습니다.");
        } catch (error: any) {
            const status = error.response?.status;
            if (status === 403) {
                setNotificationMessage("재인증이 만료되었습니다. 다시 인증해주세요.");
                router.replace("/mypage/verify");
                return;
            }
            const msg = error.response?.data?.detail || "알림 설정 저장에 실패했습니다.";
            setNotificationMessage(msg);
        } finally {
            setIsSavingNotifications(false);
        }
    }

    async function handleChangePassword() {
        setPwError("");
        setPwSuccess("");

        if (!newPw.trim()) {
            setPwError("새 비밀번호를 입력해주세요.");
            return;
        }
        if (newPw.length < 8) {
            setPwError("새 비밀번호는 8자 이상이어야 합니다.");
            return;
        }
        if (newPw !== newPw2) {
            setPwError("새 비밀번호가 일치하지 않습니다.");
            return;
        }

        if (!reauthToken) {
            setPwError("재인증 정보가 없습니다. 다시 인증해주세요.");
            router.replace("/mypage/verify");
            return;
        }

        setIsChangingPw(true);
        try {
            await api.post("/api/accounts/password/change/", {
                new_password1: newPw,
                new_password2: newPw2,
            }, {
                headers: { "X-Reauth-Token": reauthToken },
            });
            setPwSuccess("비밀번호가 성공적으로 변경되었습니다.");
            setNewPw("");
            setNewPw2("");
        } catch (error: any) {
            const data = error.response?.data;
            const status = error.response?.status;
            if (status === 403) {
                setPwError("재인증이 만료되었습니다. 다시 인증해주세요.");
                router.replace("/mypage/verify");
                return;
            }
            if (data?.error) {
                setPwError(translatePasswordError(String(data.error)));
                return;
            }
            if (data) {
                const messages = Object.values(data).flat().map((msg) => translatePasswordError(String(msg))).join(" ");
                setPwError(messages || "비밀번호 변경에 실패했습니다.");
                return;
            }
            setPwError("비밀번호 변경에 실패했습니다.");
        } finally {
            setIsChangingPw(false);
        }
    }

    async function handleDeleteAccount() {
        if (!deletePw.trim()) {
            setDeleteError("\uBE44\uBC00\uBC88\uD638\uB97C \uC785\uB825\uD574\uC8FC\uC138\uC694.");
            return;
        }
        if (!reauthToken) {
            setDeleteError("\uC7AC\uC778\uC99D \uC815\uBCF4\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC778\uC99D\uD574\uC8FC\uC138\uC694.");
            router.replace("/mypage/verify");
            return;
        }

        setIsDeleting(true);
        setDeleteError("");

        try {
            await api.delete("/api/accounts/delete/", {
                data: { password: deletePw },
                headers: { "X-Reauth-Token": reauthToken },
            });

            alert("\uD68C\uC6D0\uD0C8\uD1F4\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC774\uC6A9\uD574\uC8FC\uC154\uC11C \uAC10\uC0AC\uD569\uB2C8\uB2E4.");
            window.location.href = "/";
        } catch (error: any) {
            if (error.response?.status === 403) {
                setDeleteError("\uC7AC\uC778\uC99D\uC774 \uB9CC\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC778\uC99D\uD574\uC8FC\uC138\uC694.");
                router.replace("/mypage/verify");
                return;
            }
            const message = error.response?.data?.error || "\uD68C\uC6D0\uD0C8\uD1F4\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4.";
            setDeleteError(message);
        } finally {
            setIsDeleting(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="text-sm text-gray-500">홈 &gt; 마이페이지 &gt; 나의정보관리 &gt; 내 정보 수정하기</div>
            <h1 className="text-3xl font-bold">내 정보 수정하기</h1>

            <div className="rounded-2xl bg-gray-50 p-5 text-sm text-gray-600">
                <ul className="list-disc space-y-1 pl-5">
                    <li>중요 개인정보는 신중히 취급하며, 인증 이후에만 변경 가능합니다.</li>
                </ul>
            </div>

            {/* 개인정보 (읽기전용) */}
            <section className="border-t border-gray-200 bg-white px-6 pt-6">
                <div className="mb-4 text-lg font-bold">개인회원정보</div>

                <div className="grid gap-4 md:grid-cols-2">
                    {form.hasPassword && (
                        <label className="block">
                            <div className="mb-1 text-xs text-gray-600">아이디(로그인용)</div>
                            <input
                                value={form.displayName || "-"}
                                readOnly
                                className="h-11 w-full rounded-lg border bg-gray-50 px-3 text-sm text-gray-500 outline-none cursor-not-allowed"
                            />
                        </label>
                    )}

                    <label className="block">
                        <div className="mb-1 text-xs text-gray-600">이메일</div>
                        <input
                            value={form.email || "-"}
                            readOnly
                            className="h-11 w-full rounded-lg border bg-gray-50 px-3 text-sm text-gray-500 outline-none cursor-not-allowed"
                        />
                    </label>

                </div>
            </section>

            {/* 정책 알림 설정 */}
            <section className="border-b border-gray-200 bg-white px-6 pb-6">
                <div className="mb-4 text-lg font-bold">📬 정책 알림 설정</div>
                <div className="space-y-4">
                    <label className="block">
                        <div className="mb-1 text-xs text-gray-600">알림받을 이메일 주소</div>
                        <input
                            type="email"
                            value={form.notificationEmail ?? form.email ?? ""}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    notificationEmail: e.target.value || null,
                                })
                            }
                            placeholder="example@email.com"
                            className="h-11 w-full max-w-md rounded-lg border px-3 text-sm outline-none focus:border-blue-800"
                        />
                    </label>

                    <label className="flex items-start gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={form.emailNotificationEnabled ?? false}
                            onChange={(e) =>
                                setForm({
                                    ...form,
                                    emailNotificationEnabled: e.target.checked,
                                })
                            }
                            className="mt-1 h-4 w-4 rounded border-gray-300"
                        />
                        <div>
                            <span className="text-sm font-semibold">정책정보 알림 수신 동의</span>
                            <p className="text-sm text-gray-600 mt-1">
                                새로운 정책이 등록되면 회원님의 프로필과 매칭되는 정책을 이메일로 알려드립니다.
                            </p>
                        </div>
                    </label>

                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={handleSaveNotifications}
                            disabled={isSavingNotifications}
                            className="rounded-lg bg-blue-800 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            {isSavingNotifications ? "저장 중..." : "알림 설정 저장"}
                        </button>
                        {notificationMessage && (
                            <span className="text-sm text-gray-600">{notificationMessage}</span>
                        )}
                    </div>
                </div>
            </section>

            {form.hasPassword ? (
                <section className="border-b border-gray-200 bg-white px-6 pb-6">
                    <div className="mb-4 text-lg font-bold">비밀번호 재설정</div>

                    <div className="grid gap-4 md:grid-cols-2">

                        <label className="block md:col-span-2">
                            <div className="mb-1 text-xs text-gray-600">기존 비밀번호</div>
                            <input
                                value="재인증 완료"
                                readOnly
                                className="h-11 w-full rounded-lg border bg-gray-50 px-3 text-sm text-gray-500 outline-none cursor-not-allowed"
                            />
                        </label>

                        <label className="block">
                            <div className="mb-1 text-xs text-gray-600">새 비밀번호</div>
                            <input
                                type="password"
                                value={newPw}
                                onChange={(e) => { setNewPw(e.target.value); setPwError(""); }}
                                placeholder="8자 이상"
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                            {newPwTooShort ? (
                                <div className="mt-1 text-[11px] text-red-500">8자 이상 입력해주세요.</div>
                            ) : null}
                            {newPwRuleInvalid ? (
                                <div className="mt-1 text-[11px] text-red-500">영문, 숫자, 특수문자를 모두 포함해주세요.</div>
                            ) : null}
                        </label>

                        <label className="block">
                            <div className="mb-1 text-xs text-gray-600">새 비밀번호 확인</div>
                            <input
                                type="password"
                                value={newPw2}
                                onChange={(e) => { setNewPw2(e.target.value); setPwError(""); }}
                                className="h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-gray-900"
                            />
                            {newPwMismatch ? (
                                <div className="mt-1 text-[11px] text-red-500">비밀번호가 일치하지 않습니다.</div>
                            ) : null}
                        </label>
                    </div>

                    {pwError && (
                        <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">{pwError}</div>
                    )}
                    {pwSuccess && (
                        <div className="mt-3 rounded-lg bg-green-50 p-3 text-sm text-green-600">{pwSuccess}</div>
                    )}

                    <button
                        type="button"
                        onClick={handleChangePassword}
                        disabled={isChangingPw || !newPw || !newPw2 || newPwTooShort || newPwMismatch || newPwRuleInvalid}
                        className="mt-4 rounded-lg bg-blue-800 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isChangingPw ? "처리 중..." : "비밀번호 변경"}
                    </button>
                </section>
            ) : (
                <section className="border-b border-gray-200 bg-white px-6 pb-6">
                    <div className="mb-2 text-lg font-bold">비밀번호</div>
                    <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-600">
                        소셜 로그인 전용 계정입니다. 비밀번호 로그인은 지원하지 않습니다.
                    </div>
                </section>
            )}


            {/* 회원탈퇴 */}
            <section className="rounded-2xl border border-red-100 bg-red-50/30 p-6">
                <div className="mb-2 text-lg font-bold text-red-700">회원탈퇴</div>
                <p className="mb-4 text-sm text-gray-600">
                    회원탈퇴 시 모든 데이터(프로필, 스크랩 등)가 삭제되며 복구할 수 없습니다.
                </p>
                <button
                    type="button"
                    onClick={() => setShowDeleteModal(true)}
                    className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                    회원탈퇴
                </button>
            </section>

            {/* 회원탈퇴 모달 */}
            {showDeleteModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
                        <h2 className="mb-4 text-xl font-bold text-red-700">회원탈퇴 확인</h2>
                        <p className="mb-4 text-sm text-gray-600">
                            정말로 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.<br />
                            탈퇴를 진행하려면 비밀번호를 입력해주세요.
                        </p>

                        <input
                            type="password"
                            placeholder="비밀번호 입력"
                            value={deletePw}
                            onChange={(e) => {
                                setDeletePw(e.target.value);
                                setDeleteError("");
                            }}
                            className="mb-2 h-11 w-full rounded-lg border px-3 text-sm outline-none focus:border-red-500"
                        />

                        {deleteError && (
                            <div className="mb-4 text-sm text-red-500">{deleteError}</div>
                        )}

                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={() => {
                                    setShowDeleteModal(false);
                                    setDeletePw("");
                                    setDeleteError("");
                                }}
                                className="flex-1 rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
                            >
                                취소
                            </button>
                            <button
                                type="button"
                                onClick={handleDeleteAccount}
                                disabled={isDeleting}
                                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                            >
                                {isDeleting ? "처리 중..." : "탈퇴하기"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* 하단 버튼 */}
            <div className="flex items-center justify-between">
                <Link href="/mypage" className="rounded-lg border px-4 py-2 text-sm">
                    이전으로
                </Link>
            </div>
        </div>
    );
}
