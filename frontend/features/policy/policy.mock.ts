// features/policy/policy.mock.ts
import { Policy } from "./policy.types";

/**
 * ✅ 목업 데이터
 * - 나중에 Django에서 내려주는 JSON 필드명에 맞춰서 교체 가능
 * - 지금은 UI/라우팅/검색 흐름을 먼저 완성하는 목적
 * - 추후 Django 붙일 때는 policy.api.ts만 바꾸면 구조 그대로 유지 가능
 */
export const MOCK_POLICIES: Policy[] = [
    {
        id: "seoul-youth-rent-001",
        title: "서울시 청년 월세 지원",
        summary: "서울 거주 청년에게 월세를 일부 지원합니다. 신청 요건을 확인하세요.",
        category: "housing",
        region: "서울시",
        target: "만 19~39세 서울 거주 청년(소득 요건 등)",
        period: "2026.01.01 ~ 2026.02.15",
        criteria: "소득/거주/무주택 여부 등 조건 충족 시 선발",
        content:
            "월세 부담 완화를 위해 월세를 일부 지원합니다. 제출서류(임대차계약서 등)와 소득 기준을 확인 후 신청하세요.",
        isPriority: true,
        isYouth: true,

        // ✅ 달력용 임시 필드(나중에 Django에서 내려주면 그대로 교체)
        aplyYmd: "20260105 ~ 20260215",
        bizPrdBgngYmd: "20260220",
        bizPrdEndYmd: "20261231",
    },
    {
        id: "seoul-youth-job-002",
        title: "서울 청년 취업 지원 패키지",
        summary: "취업 준비 청년에게 상담/교육/훈련 프로그램을 제공합니다.",
        category: "job",
        region: "서울시",
        target: "취업 준비 청년",
        period: "상시(회차별 모집)",
        criteria: "프로그램별 기준에 따라 선발",
        content:
            "1:1 취업 컨설팅, 이력서/면접 코칭, 직무 교육 등으로 구성됩니다. 회차별 신청 기간과 선발 방식이 다를 수 있습니다.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-mind-care-003",
        title: "청년 마음 건강 상담 지원",
        summary: "심리 상담/검사 비용을 지원합니다. 초기 상담부터 연계까지 제공합니다.",
        category: "emotional-wellbeing",
        region: "서울시",
        target: "심리 지원이 필요한 청년",
        period: "2026.01.10 ~ 2026.03.31",
        criteria: "선착순/우선순위(상황에 따라)",
        content:
            "상담기관 연계 및 상담비 일부 지원. 상담 회기/지원 범위는 정책 운영 기준에 따릅니다.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-youth-rent-001",
        title: "서울시 청년 월세 지원",
        summary: "서울 거주 청년에게 월세를 일부 지원합니다. 신청 요건을 확인하세요.",
        category: "housing",
        region: "서울시",
        target: "만 19~39세 서울 거주 청년(소득 요건 등)",
        period: "2026.01.01 ~ 2026.02.15",
        criteria: "소득/거주/무주택 여부 등 조건 충족 시 선발",
        content:
            "월세 부담 완화를 위해 월세를 일부 지원합니다. 제출서류(임대차계약서 등)와 소득 기준을 확인 후 신청하세요.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-youth-job-002",
        title: "서울 청년 취업 지원 패키지",
        summary: "취업 준비 청년에게 상담/교육/훈련 프로그램을 제공합니다.",
        category: "job",
        region: "서울시",
        target: "취업 준비 청년",
        period: "상시(회차별 모집)",
        criteria: "프로그램별 기준에 따라 선발",
        content:
            "1:1 취업 컨설팅, 이력서/면접 코칭, 직무 교육 등으로 구성됩니다. 회차별 신청 기간과 선발 방식이 다를 수 있습니다.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-mind-care-003",
        title: "청년 마음 건강 상담 지원",
        summary: "심리 상담/검사 비용을 지원합니다. 초기 상담부터 연계까지 제공합니다.",
        category: "emotional-wellbeing",
        region: "서울시",
        target: "심리 지원이 필요한 청년",
        period: "2026.01.10 ~ 2026.03.31",
        criteria: "선착순/우선순위(상황에 따라)",
        content:
            "상담기관 연계 및 상담비 일부 지원. 상담 회기/지원 범위는 정책 운영 기준에 따릅니다.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-youth-rent-001",
        title: "서울시 청년 월세 지원",
        summary: "서울 거주 청년에게 월세를 일부 지원합니다. 신청 요건을 확인하세요.",
        category: "housing",
        region: "서울시",
        target: "만 19~39세 서울 거주 청년(소득 요건 등)",
        period: "2026.01.01 ~ 2026.02.15",
        criteria: "소득/거주/무주택 여부 등 조건 충족 시 선발",
        content:
            "월세 부담 완화를 위해 월세를 일부 지원합니다. 제출서류(임대차계약서 등)와 소득 기준을 확인 후 신청하세요.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-youth-job-002",
        title: "서울 청년 취업 지원 패키지",
        summary: "취업 준비 청년에게 상담/교육/훈련 프로그램을 제공합니다.",
        category: "job",
        region: "서울시",
        target: "취업 준비 청년",
        period: "상시(회차별 모집)",
        criteria: "프로그램별 기준에 따라 선발",
        content:
            "1:1 취업 컨설팅, 이력서/면접 코칭, 직무 교육 등으로 구성됩니다. 회차별 신청 기간과 선발 방식이 다를 수 있습니다.",
        isPriority: true,
        isYouth: true,
    },
    {
        id: "seoul-mind-care-003",
        title: "청년 마음 건강 상담 지원",
        summary: "심리 상담/검사 비용을 지원합니다. 초기 상담부터 연계까지 제공합니다.",
        category: "emotional-wellbeing",
        region: "서울시",
        target: "심리 지원이 필요한 청년",
        period: "2026.01.10 ~ 2026.03.31",
        criteria: "선착순/우선순위(상황에 따라)",
        content:
            "상담기관 연계 및 상담비 일부 지원. 상담 회기/지원 범위는 정책 운영 기준에 따릅니다.",
        isPriority: true,
        isYouth: true,
    },
    // 필요하면 더 추가
];
