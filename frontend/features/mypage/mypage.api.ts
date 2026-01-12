// features/mypage/mypage.api.ts
"use client";

import { MOCK_PROFILE, MOCK_VERIFY } from "./mypage.mock";
import type { MyProfile, VerifyState } from "./mypage.types";

const PROFILE_KEY = "welfarecompass:mypage_profile";
const VERIFY_KEY = "welfarecompass:verify_state";

export async function getMyProfile(): Promise<MyProfile> {
    await new Promise((r) => setTimeout(r, 60));
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return MOCK_PROFILE;
    try {
        return JSON.parse(raw) as MyProfile;
    } catch {
        return MOCK_PROFILE;
    }
}

export async function saveMyProfile(profile: MyProfile): Promise<void> {
    await new Promise((r) => setTimeout(r, 120));
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
}

export async function getVerifyState(): Promise<VerifyState> {
    await new Promise((r) => setTimeout(r, 30));
    const raw = localStorage.getItem(VERIFY_KEY);
    if (!raw) return MOCK_VERIFY;
    try {
        return JSON.parse(raw) as VerifyState;
    } catch {
        return MOCK_VERIFY;
    }
}

export async function setVerified(): Promise<void> {
    await new Promise((r) => setTimeout(r, 150));
    const next: VerifyState = { isVerified: true, verifiedAt: new Date().toISOString() };
    localStorage.setItem(VERIFY_KEY, JSON.stringify(next));
}

export async function clearVerified(): Promise<void> {
    await new Promise((r) => setTimeout(r, 80));
    localStorage.setItem(VERIFY_KEY, JSON.stringify({ isVerified: false }));
}
