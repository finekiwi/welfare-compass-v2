// features/policy/policy.mock.ts
import { Policy } from "./policy.types";

/**
 * ✅ 목업 데이터 (중복 id 금지)
 * - isPriority / isYouth는 섹션 노출 테스트용
 * - region, category 섞어서 검색/필터 UI 테스트 가능
 */
export const MOCK_POLICIES: Policy[] = [
    // ---- 청년(Youth) ----
    {
        id: "mock-youth-rent-001",
        title: "서울시 청년 월세 지원",
        summary: "서울 거주 청년에게 월세를 일부 지원합니다. 소득/거주 요건 확인 후 신청하세요.",
        category: "housing",
        region: "서울시",
        target: "만 19~39세 서울 거주 청년(소득 요건 등)",
        period: "2026.01.01 ~ 2026.02.15",
        criteria: "소득/거주/무주택 여부 등 조건 충족 시 선발",
        content: "월세 부담 완화를 위해 월세를 일부 지원합니다. 제출서류 및 소득 기준 확인 후 신청하세요.",
        isPriority: true,
        isYouth: true,
        aplyYmd: "20260101 ~ 20260215",
        bizPrdBgngYmd: "20260220",
        bizPrdEndYmd: "20261231",
    },
    {
        id: "mock-youth-job-002",
        title: "청년 취업 지원 패키지",
        summary: "취업 준비 청년에게 상담/교육/훈련을 지원합니다. 회차별 모집 일정 확인 필요.",
        category: "job",
        region: "서울시",
        target: "취업 준비 청년",
        period: "상시(회차별 모집)",
        criteria: "프로그램별 기준에 따라 선발",
        content: "1:1 취업 컨설팅, 이력서/면접 코칭, 직무 교육 등으로 구성됩니다.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "mock-youth-mind-003",
        title: "청년 마음건강 상담 지원",
        summary: "심리 상담/검사 비용을 지원합니다. 초기 상담부터 기관 연계까지 제공합니다.",
        category: "emotional-wellbeing",
        region: "서울시",
        target: "심리 지원이 필요한 청년",
        period: "2026.01.10 ~ 2026.03.31",
        criteria: "선착순 또는 우선순위 기준 적용",
        content: "상담기관 연계 및 상담비 일부 지원. 상담 회기/지원 범위는 운영 기준에 따릅니다.",
        isPriority: true,
        isYouth: true,
    },

    // ---- 신혼부부 / 주거 ----
    {
        id: "mock-newlywed-loan-004",
        title: "신혼부부 전세자금 대출 이자 지원",
        summary: "신혼부부의 주거비 부담 완화를 위해 전세자금 대출 이자를 일부 지원합니다.",
        category: "housing",
        region: "서울시",
        target: "혼인 기간 요건을 충족하는 신혼부부(소득/주택 요건 등)",
        period: "2026.02.01 ~ 2026.04.30",
        criteria: "소득/무주택/전세 계약 요건 충족 시",
        content: "전세자금 대출 이자의 일부를 지원합니다. 지원 한도 및 제출서류는 공고문 기준.",
        isPriority: true,
    },
    {
        id: "mock-newlywed-house-005",
        title: "신혼부부 주택 특별공급 안내(목업)",
        summary: "신혼부부 대상 특별공급 자격/서류/신청 절차를 안내합니다.",
        category: "housing",
        region: "전국",
        target: "혼인 및 무주택 요건을 충족하는 신혼부부",
        period: "공고 시 상이",
        criteria: "특별공급 공고문 기준(무주택/소득/자산 등)",
        content: "공공/민영주택 특별공급 신청 절차 및 제출서류를 안내합니다.",
    },

    // ---- 생활·금융 ----
    {
        id: "mock-finance-energy-006",
        title: "저소득 가구 에너지바우처 지원(목업)",
        summary: "냉난방 비용 부담 완화를 위한 에너지 바우처를 지원합니다.",
        category: "finance",
        region: "전국",
        target: "소득/세대 조건을 충족하는 취약계층",
        period: "2026년 하절기/동절기(시기별 운영)",
        criteria: "대상 요건 충족 여부(행정 확인)",
        content: "하절기/동절기에 사용할 수 있는 에너지 바우처를 제공합니다.",
        isPriority: true,
    },
    {
        id: "mock-finance-childcare-007",
        title: "아동 양육수당/가정양육 지원(목업)",
        summary: "가정양육 가구에 양육 관련 수당을 지원합니다. 연령/소득 요건은 제도별 상이.",
        category: "care-protection",
        region: "전국",
        target: "아동을 양육하는 가구(제도별 요건 상이)",
        period: "상시",
        criteria: "연령/거주/신청 요건 충족 시",
        content: "아동 연령 및 제도 기준에 따라 양육수당을 지원합니다.",
    },

    // ---- 창업 ----
    {
        id: "mock-startup-seed-008",
        title: "예비창업자 시드 지원 프로그램(목업)",
        summary: "예비창업자를 대상으로 사업화 자금/멘토링/교육을 지원합니다.",
        category: "entrepreneurship",
        region: "서울시",
        target: "예비창업자 또는 초기 창업자(기간 요건 등)",
        period: "2026.03.01 ~ 2026.03.31",
        criteria: "서류/발표 평가 등 프로그램 기준",
        content: "사업화 자금 일부 및 멘토링/교육 프로그램을 제공합니다.",
    },

    // ---- 정신건강 ----
    {
        id: "mock-mental-screening-009",
        title: "정신건강 선별검사 및 상담 연계(목업)",
        summary: "정신건강 선별검사 후 필요 시 상담기관/치료로 연계합니다.",
        category: "mental-health",
        region: "서울시",
        target: "정신건강 검사가 필요한 시민(대상은 프로그램에 따라 상이)",
        period: "상시(기관 운영시간 내)",
        criteria: "기관 기준 및 상담 가능 여부",
        content: "선별검사 후 결과에 따라 상담기관 및 치료 연계를 지원합니다.",
    },

    // ---- 보호·돌봄 / 장애 / 가족 ----
    {
        id: "mock-care-disability-010",
        title: "장애인 활동지원 서비스(목업)",
        summary: "일상생활 지원이 필요한 장애인에게 활동지원 서비스를 제공합니다.",
        category: "care-protection",
        region: "전국",
        target: "활동지원이 필요한 등록 장애인(등급/점수 기준 등)",
        period: "상시",
        criteria: "인정조사 점수 및 대상 요건 충족",
        content: "활동지원사의 방문 지원(신체활동/가사/이동 등) 서비스를 제공합니다.",
        isPriority: true,
    },
    {
        id: "mock-care-singleparent-011",
        title: "한부모가정 생활 지원(목업)",
        summary: "한부모가정의 생활안정 및 자녀양육 지원을 제공합니다.",
        category: "care-protection",
        region: "전국",
        target: "한부모가정(소득/자녀 요건 등)",
        period: "상시",
        criteria: "소득 및 가구 요건 충족 시",
        content: "생활비, 양육비, 교육비 등 제도별 지원을 제공합니다.",
    },

    // ---- 기타: 다자녀/주거/금융 혼합 ----
    {
        id: "mock-housing-multichild-012",
        title: "다자녀 가구 주거 지원(목업)",
        summary: "다자녀 가구의 주거 안정 지원(우선공급/지원제도 등)을 제공합니다.",
        category: "housing",
        region: "서울시",
        target: "다자녀 가구(자녀 수/거주 요건 등)",
        period: "공고 시 상이",
        criteria: "다자녀 요건 및 공고 기준 충족",
        content: "우선공급, 지원제도 안내 및 신청 절차를 제공합니다.",
    },
];

/**
 * ✅ Youth 섹션 전용(카드용 최소 필드만 쓰고 싶으면)
 * - 지금 PolicyCard가 PolicyCardItem을 받으므로 최소 필드만으로도 OK
 * - 다만 YouthPolicySection이 fetchYouthPolicies를 쓰면 이 배열은 안 나옴(직접 import 필요)
 */
export const YOUTH_POLICIES_MOCK = [
    {
        id: "youth-card-001",
        title: "청년 전월세 보증금 지원(목업)",
        summary: "청년의 보증금 부담 완화를 위한 지원 프로그램입니다.",
        region: "서울시",
    },
    {
        id: "youth-card-002",
        title: "청년 구직활동 지원금(목업)",
        summary: "구직활동 비용(교육/면접/교통 등) 일부를 지원합니다.",
        region: "서울시",
    },
    {
        id: "youth-card-003",
        title: "청년 심리상담 바우처(목업)",
        summary: "상담비 일부를 바우처 형태로 지원합니다.",
        region: "서울시",
    },
] as const;
