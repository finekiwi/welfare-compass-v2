// features/mypage/mypage.mock.ts
import type { MyProfile, VerifyState } from "./mypage.types";

export const MOCK_PROFILE: MyProfile = {
    // UI 표시용
    displayName: "복지나침반 사용자",
    avatarUrl: "/images/beluga.png",

    // 기본 정보
    birthYear: 2000,           // 만 26세 (2026년 기준)
    district: "마포구",

    // 소득/취업
    incomeLevel: "below_100",
    incomeAmount: 200,         // 월 200만원
    jobStatus: "job_seeking",

    // 학력
    educationStatus: "graduated",

    // 결혼
    marriageStatus: "single",

    // 주거 정보
    housingType: "monthly",    // 월세

    // 가구 정보
    householdSize: 1,          // 1인 가구

    // 자녀 정보
    hasChildren: false,
    childrenAges: [],

    // 특수 조건
    specialConditions: [],

    // 필요 분야
    needs: ["주거", "일자리"],

    // 관심 분야 IDs
    interestIds: [],

    // 이메일 알림 설정
    emailNotificationEnabled: false,
    notificationEmail: null,

    // 연락처
    phone: "010-0000-0000",
    email: "user@example.com",
};

export const MOCK_VERIFY: VerifyState = {
    isVerified: false,
};
