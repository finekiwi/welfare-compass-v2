import type { PolicyCategory } from "./policy.types";

export const CATEGORY_NAME_MAP: Record<string, PolicyCategory> = {
  "일자리": "job",
  "주거": "housing",
  "교육": "education",
  "복지문화": "welfare",
  "참여권리": "participation",
  // Fallbacks for old/grouped labels
  "금융": "welfare",
  "창업": "job",
  "복지": "welfare",
  "문화": "welfare",
};

export const CATEGORY_LABELS: Record<PolicyCategory, string> = {
  job: "일자리",
  housing: "주거",
  education: "교육",
  welfare: "복지·문화",
  participation: "참여·권리",
};

export function getCategoryLabel(category: PolicyCategory | string): string {
  if (!category) return "기타";
  if (CATEGORY_LABELS[category as PolicyCategory]) {
    return CATEGORY_LABELS[category as PolicyCategory];
  }
  if (category in CATEGORY_NAME_MAP) {
    return CATEGORY_LABELS[CATEGORY_NAME_MAP[category]];
  }
  return category;
}

export function toPolicyCategoryFromName(name?: string): PolicyCategory {
  if (!name) return "welfare";
  if (name.includes("일자리") || name.includes("창업")) return "job";
  if (name.includes("주거")) return "housing";
  if (name.includes("교육")) return "education";
  if (name.includes("참여") || name.includes("권리")) return "participation";
  return "welfare";
}

export const JOB_STATUS_TO_API: Record<string, string> = {
  employed: "0013001",
  self_employed: "0013002",
  unemployed: "0013003",
  job_seeking: "0013003",
  student: "0013003",
  startup: "0013006",
  freelancer: "0013004",
};

export const EDUCATION_STATUS_TO_API: Record<string, string> = {
  below_high_school: "0049001",
  high_school_enrolled: "0049002",
  high_school: "0049004",
  university_enrolled: "0049005",
  university_leave: "0049005",
  university: "0049007",
  graduate_school: "0049008",
};

export const MARRIAGE_STATUS_TO_API: Record<string, string> = {
  single: "0055002",
  married: "0055001",
};
