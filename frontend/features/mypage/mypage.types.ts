// features/mypage/mypage.types.ts

// =========================================================================
// 백엔드 Profile 모델과 동일한 타입 정의 (matching.py 호환)
// =========================================================================

// 취업 상태 (Backend: JOB_STATUS_CHOICES)
export type JobStatus =
    | "employed"      // 재직중
    | "unemployed"    // 미취업
    | "job_seeking"   // 구직중
    | "student"       // 학생
    | "startup"       // 창업준비
    | "freelancer"    // 프리랜서
    | "other";        // 기타

// 학력 상태 (Backend: EDUCATION_STATUS_CHOICES)
export type EducationStatus =
    | "enrolled"   // 재학
    | "on_leave"   // 휴학
    | "graduated"  // 졸업
    | "dropout"    // 중퇴
    | "other";     // 기타

// 혼인 상태 (Backend: MARRIAGE_STATUS_CHOICES)
export type MarriageStatus =
    | "single"   // 미혼
    | "married"  // 기혼
    | "other";   // 기타

// 소득 수준 (Backend: INCOME_LEVEL_CHOICES)
export type IncomeLevel =
    | "below_50"   // 기준중위소득 50% 이하
    | "below_100"  // 기준중위소득 100% 이하
    | "above_100"  // 기준중위소득 100% 초과
    | "unknown";   // 모름

// 주거 형태 (Backend: HOUSING_TYPE_CHOICES)
export type HousingType =
    | "jeonse"   // 전세
    | "monthly"  // 월세
    | "owned"    // 자가
    | "gosiwon"  // 고시원
    | "parents"  // 부모님집
    | "public"   // 공공임대
    | "other";   // 기타

// 특수 조건 (matching.py에서 사용하는 값)
export type SpecialCondition =
    | "신혼"
    | "한부모"
    | "장애"
    | "장애인"
    | "기초수급"
    | "기초수급자"
    | "수급자";

// 관심/필요 분야 (대분류 카테고리)
export type NeedCategory =
    | "주거"
    | "일자리"
    | "복지문화"
    | "교육"
    | "건강";

// 서울시 25개 구
export const SEOUL_DISTRICTS = [
    "종로구", "중구", "용산구", "성동구", "광진구",
    "동대문구", "중랑구", "성북구", "강북구", "도봉구",
    "노원구", "은평구", "서대문구", "마포구", "양천구",
    "강서구", "구로구", "금천구", "영등포구", "동작구",
    "관악구", "서초구", "강남구", "송파구", "강동구"
] as const;

export type SeoulDistrict = typeof SEOUL_DISTRICTS[number];

// =========================================================================
// 프로필 타입 (Backend Profile 모델과 1:1 매핑)
// =========================================================================
export type MyProfile = {
    // UI 표시용
    displayName: string;
    avatarUrl?: string;

    // 기본 정보
    birthYear: number | null;      // 출생년도 (나이 계산용)
    district: string;              // 거주 구 (서울시 25개 구 중 하나)

    // 소득/취업
    incomeLevel: IncomeLevel | "";      // 소득 수준
    incomeAmount: number | null;        // 월 소득 (만원)
    jobStatus: JobStatus | "";          // 취업 상태

    // 학력
    educationStatus: EducationStatus | "";  // 학력 상태

    // 결혼
    marriageStatus: MarriageStatus | "";    // 혼인 상태

    // 주거 정보 (matching.py 핵심 필드)
    housingType: HousingType | "";          // 주거 형태

    // 가구 정보
    householdSize: number | null;           // 가구원 수 (본인 포함)

    // 자녀 정보
    hasChildren: boolean;                   // 자녀 유무
    childrenAges: number[];                 // 자녀 나이 리스트

    // 특수 조건 (신혼, 한부모, 장애 등)
    specialConditions: SpecialCondition[];

    // 필요 분야 (다중 선택)
    needs: NeedCategory[];

    // 관심 분야 IDs (Category M:N)
    interestIds: number[];

    // 이메일 알림 설정
    emailNotificationEnabled: boolean;      // 정책정보 알림 수신 동의
    notificationEmail: string | null;       // 알림 수신 이메일

    // 연락처 (본인인증 후 수정)
    phone: string;
    email: string;
};

// =========================================================================
// 본인인증 상태
// =========================================================================
export type VerifyState = {
    isVerified: boolean;
    verifiedAt?: string; // ISO
};

// =========================================================================
// 스크랩 타입
// =========================================================================
export interface Scrap {
    id: number;
    plcy_no: string;
    plcy_nm: string;
    plcy_expln_cn: string;
    district: string;
    category: string;
    created_at: string;
}
