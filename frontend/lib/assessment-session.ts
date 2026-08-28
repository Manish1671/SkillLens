import type { AssessmentPlanItem, AssessmentPlanResponse } from "@/lib/api";

const STORAGE_PREFIX = "skilllens.assessment.v1.";

export type StoredAssessmentSession = {
  userId: string;
  assessmentId: string;
  dimension: string | null;
  session: number;
  index: number;
  complete: boolean;
  plan: AssessmentPlanResponse;
};

export function assessmentStorageKey(userId: string): string {
  return `${STORAGE_PREFIX}${userId}`;
}

export function clientAttemptId(assessmentId: string, position: number, session: number): string {
  const compact = assessmentId.replaceAll("-", "").slice(0, 20);
  return `ap-${compact}-p${position}-s${session}`.slice(0, 64);
}

export function loadAssessmentSession(userId: string): StoredAssessmentSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(assessmentStorageKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredAssessmentSession;
    if (parsed.userId !== userId || !parsed.plan?.items) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveAssessmentSession(session: StoredAssessmentSession): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(assessmentStorageKey(session.userId), JSON.stringify(session));
}

export function clearAssessmentSession(userId: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(assessmentStorageKey(userId));
}

export function fingerprintPlan(items: AssessmentPlanItem[]): string {
  return items.map((item) => `${item.position}:${item.problem_slug}`).join("|");
}
