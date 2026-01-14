// features/mypage/mypage.mock.ts
import type { MyProfile, VerifyState } from "./mypage.types";

export const MOCK_PROFILE: MyProfile = {
    displayName: "복지나침반 사용자",
    avatarUrl: "/images/beluga.png", // 없으면 공백 처리됨

    interestDistrict: "서울 종로구 외 24",
    age: 24,
    maritalStatus: "single",

    incomeMin: null,
    incomeMax: null,

    education: "college_grad",
    jobStatus: "none",
    majorField: "none",
    specialtyField: "none",

    phone: "010-0000-0000",
    email: "user@example.com",
};

export const MOCK_VERIFY: VerifyState = {
    isVerified: false,
};
