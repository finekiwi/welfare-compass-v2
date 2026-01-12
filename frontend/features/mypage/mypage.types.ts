// features/mypage/mypage.types.ts

export type MaritalStatus = "none" | "single" | "married";
export type Education =
    | "none"
    | "lt_high"
    | "high_in_school"
    | "high_expected"
    | "high_grad"
    | "college_in_school"
    | "college_expected"
    | "college_grad"
    | "graduate"
    | "other";

export type JobStatus =
    | "none"
    | "worker"
    | "self_employed"
    | "unemployed"
    | "freelancer"
    | "daily_worker"
    | "startup_preparing"
    | "short_term_worker"
    | "agriculture"
    | "military"
    | "local_talent"
    | "other";

export type MajorField =
    | "none"
    | "humanities"
    | "social"
    | "business"
    | "science"
    | "engineering"
    | "arts"
    | "agriculture"
    | "other";

export type SpecialtyField =
    | "none"
    | "sme"
    | "women"
    | "basic_living"
    | "single_parent"
    | "disabled"
    | "agriculture"
    | "military"
    | "local_talent"
    | "other";

export type MyProfile = {
    displayName: string;
    avatarUrl?: string;

    // 퍼스널 정보(정책 추천/필터용)
    interestDistrict: string; // 예: "서울 종로구 외 24" 느낌으로 표기
    age: number | null;
    maritalStatus: MaritalStatus;

    incomeMin: number | null; // 만원
    incomeMax: number | null; // 만원

    education: Education;
    jobStatus: JobStatus;
    majorField: MajorField;
    specialtyField: SpecialtyField;

    // 중요 개인정보(본인인증 후 수정)
    phone: string; // 표시용(실서비스면 마스킹/별도 처리)
    email: string;
};

export type VerifyState = {
    isVerified: boolean;
    verifiedAt?: string; // ISO
};
