// features/mypage/mypage.api.ts
"use client";

import { api } from "@/services/axios";
import { MOCK_PROFILE, MOCK_VERIFY } from "./mypage.mock";
import type { MyProfile, VerifyState } from "./mypage.types";

const VERIFY_KEY = "welfarecompass:verify_state";

// =========================================================================
// 백엔드 Profile API 응답 타입 (snake_case)
// =========================================================================
interface BackendProfile {
    username: string;
    email: string;
    birth_year: number | null;
    district: string;
    income_level: string;
    income_amount: number | null;
    job_status: string;
    education_status: string;
    marriage_status: string;
    housing_type: string;
    household_size: number | null;
    has_children: boolean;
    children_ages: number[];
    special_conditions: string[];
    needs: string[];
    interests: number[];
    interests_display: string[];
    age: number | null;
    email_notification_enabled?: boolean;
    notification_email?: string | null;
    created_at: string;
    updated_at: string;
    has_password?: boolean;
}

// =========================================================================
// 백엔드 → 프론트엔드 변환
// =========================================================================
function toFrontendProfile(backend: BackendProfile): MyProfile {
    return {
        displayName: backend.username,
        avatarUrl: undefined,
        birthYear: backend.birth_year,
        district: backend.district || "",
        incomeLevel: (backend.income_level || "") as MyProfile["incomeLevel"],
        incomeAmount: backend.income_amount,
        jobStatus: (backend.job_status || "") as MyProfile["jobStatus"],
        educationStatus: (backend.education_status || "") as MyProfile["educationStatus"],
        marriageStatus: (backend.marriage_status || "") as MyProfile["marriageStatus"],
        housingType: (backend.housing_type || "") as MyProfile["housingType"],
        householdSize: backend.household_size,
        hasChildren: backend.has_children,
        childrenAges: backend.children_ages || [],
        specialConditions: (backend.special_conditions || []) as MyProfile["specialConditions"],
        needs: (backend.needs || []) as MyProfile["needs"],
        interestIds: backend.interests || [],
        emailNotificationEnabled: backend.email_notification_enabled ?? false,
        notificationEmail: backend.notification_email || null,
        phone: "",
        email: backend.email || "",
        hasPassword: backend.has_password ?? true,
    };
}

// =========================================================================
// 프론트엔드 → 백엔드 변환
// =========================================================================
function toBackendProfile(frontend: MyProfile): Partial<BackendProfile> {
    return {
        birth_year: frontend.birthYear,
        district: frontend.district,
        income_level: frontend.incomeLevel || undefined,
        income_amount: frontend.incomeAmount,
        job_status: frontend.jobStatus || undefined,
        education_status: frontend.educationStatus || undefined,
        marriage_status: frontend.marriageStatus || undefined,
        housing_type: frontend.housingType || undefined,
        household_size: frontend.householdSize,
        has_children: frontend.hasChildren,
        children_ages: frontend.childrenAges,
        special_conditions: frontend.specialConditions,
        needs: frontend.needs,
        interests: frontend.interestIds,
        email_notification_enabled: frontend.emailNotificationEnabled,
        notification_email: frontend.notificationEmail,
    };
}

// =========================================================================
// API 함수
// =========================================================================
export async function getMyProfile(): Promise<MyProfile> {
    try {
        const response = await api.get<BackendProfile>("/api/accounts/profile/");
        return toFrontendProfile(response.data);
    } catch (error) {
        console.error("getMyProfile error:", error);
        // 로그인 안 된 경우 등 에러 시 기본값 반환
        return MOCK_PROFILE;
    }
}

export async function saveMyProfile(profile: MyProfile, token?: string): Promise<void> {
    const backendData = toBackendProfile(profile);
    const headers = token ? { "X-Reauth-Token": token } : {};
    await api.put("/api/accounts/profile/", backendData, { headers });
}

export async function getVerifyState(): Promise<VerifyState> {
    await new Promise((r) => setTimeout(r, 30));
    const raw = sessionStorage.getItem(VERIFY_KEY);
    if (!raw) return MOCK_VERIFY;
    try {
        return JSON.parse(raw) as VerifyState;
    } catch {
        return MOCK_VERIFY;
    }
}

export async function setVerified(token?: string): Promise<void> {
    await new Promise((r) => setTimeout(r, 150));
    const next: VerifyState = { isVerified: true, reauthToken: token, verifiedAt: new Date().toISOString() };
    sessionStorage.setItem(VERIFY_KEY, JSON.stringify(next));
}


export async function clearVerified(): Promise<void> {
    await new Promise((r) => setTimeout(r, 80));
    sessionStorage.setItem(VERIFY_KEY, JSON.stringify({ isVerified: false }));
}

// =========================================================================
// [스크랩 API]
// =========================================================================
import { Scrap } from "./mypage.types";

export interface ScrapListResponse {
    results: {
        id: number;
        policy: {
            plcy_no: string;
            plcy_nm: string;
            plcy_expln_cn: string;
            district: string | null;
            categories: { id: number; name: string }[];
            poster_url?: string | null;
        };
        created_at: string;
    }[];
}

/**
 * ✅ 내 스크랩 목록 조회
 */
export async function fetchScraps(): Promise<Scrap[]> {
    try {
        const response = await api.get<ScrapListResponse>("/api/accounts/scraps/");
        return response.data.results.map((item) => ({
            id: item.id,
            plcy_no: item.policy.plcy_no,
            plcy_nm: item.policy.plcy_nm,
            plcy_expln_cn: item.policy.plcy_expln_cn,
            district: item.policy.district || "전국",
            category: item.policy.categories?.[0]?.name || "기타",
            created_at: item.created_at,
            posterUrl: item.policy.poster_url ?? null,
        }));
    } catch (error: any) {
        if (error.response?.status !== 401) {
            console.error("fetchScraps error:", error);
        }
        return [];
    }
}

/**
 * ✅ 스크랩 추가
 */
export async function addScrap(policyId: string): Promise<boolean> {
    try {
        await api.post(`/api/accounts/scraps/${policyId}/`);
        return true;
    } catch (error) {
        console.error("addScrap error:", error);
        return false;
    }
}

/**
 * ✅ 스크랩 삭제
 */
export async function removeScrap(policyId: string): Promise<boolean> {
    try {
        await api.delete(`/api/accounts/scraps/${policyId}/`);
        return true;
    } catch (error) {
        console.error("removeScrap error:", error);
        return false;
    }
}
