export type PublicUser = {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
};

export type ApiErrorBody = {
  detail: string;
  code: string;
};

async function parseJson<T>(response: Response): Promise<T> {
  return response.json() as Promise<T>;
}

export async function registerUser(input: {
  email: string;
  password: string;
  display_name: string;
}): Promise<{ data?: PublicUser; error?: ApiErrorBody; status: number }> {
  const response = await fetch("/api/auth/register", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<PublicUser>(response), status: response.status };
}

export async function loginUser(input: {
  email: string;
  password: string;
}): Promise<{ data?: PublicUser; error?: ApiErrorBody; status: number }> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<PublicUser>(response), status: response.status };
}

export async function getCurrentUser(): Promise<{
  data?: PublicUser;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/auth/me", {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<PublicUser>(response), status: response.status };
}

export async function logoutUser(): Promise<{ status: number }> {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  return { status: response.status };
}

export type TopicSummary = {
  slug: string;
  name: string;
  sort_order: number;
};

export type SkillSummary = {
  slug: string;
  name: string;
  description: string;
  topic_slug: string | null;
  is_foundational: boolean;
  sort_order: number;
  prerequisite_skill_ids: string[];
};

export type ProblemSkillLink = {
  slug: string;
  name: string;
  weight: string;
  is_primary: boolean;
};

export type LearnerProblemState = {
  attempted: boolean;
  solved: boolean;
  in_progress: boolean;
};

export type ActivityKind = "coding" | "quiz";

export type QuizOption = {
  id: string;
  label: string;
};

export type ProblemListItem = {
  id: string;
  slug: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  activity_kind?: ActivityKind;
  topic: TopicSummary;
  skills: ProblemSkillLink[];
  learner_state: LearnerProblemState | null;
};

export type ProblemListResponse = {
  items: ProblemListItem[];
  next_cursor: string | null;
  has_more: boolean;
};

export type ProblemDetail = {
  id: string;
  slug: string;
  title: string;
  prompt_md: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  activity_kind?: ActivityKind;
  topic: TopicSummary;
  skills: ProblemSkillLink[];
  hint_count: number;
  options?: QuizOption[] | null;
  learner_state: LearnerProblemState | null;
};

export type ProblemFilters = {
  topic?: string;
  skill?: string;
  difficulty?: "easy" | "medium" | "hard";
  activity_kind?: ActivityKind | "all";
  q?: string;
  cursor?: string;
  limit?: number;
};

function buildQueryString(filters: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listTopics(): Promise<{
  data?: TopicSummary[];
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/topics", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<TopicSummary[]>(response), status: response.status };
}

export async function listSkills(): Promise<{
  data?: SkillSummary[];
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/skills", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<SkillSummary[]>(response), status: response.status };
}

export type CatalogSkillDetail = {
  slug: string;
  name: string;
  description: string;
  topic_slug: string | null;
  is_foundational: boolean;
  sort_order: number;
  prerequisites: SkillSummary[];
  dependents: SkillSummary[];
  linked_problems: {
    slug: string;
    title: string;
    difficulty: "easy" | "medium" | "hard";
    estimated_minutes: number;
  }[];
};

export async function getSkill(slug: string): Promise<{
  data?: CatalogSkillDetail;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch(`/api/skills/${slug}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<CatalogSkillDetail>(response), status: response.status };
}

export async function listProblems(filters: ProblemFilters = {}): Promise<{
  data?: ProblemListResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const query = buildQueryString({
    topic: filters.topic,
    skill: filters.skill,
    difficulty: filters.difficulty,
    activity_kind: filters.activity_kind,
    q: filters.q,
    cursor: filters.cursor,
    limit: filters.limit,
  });
  const response = await fetch(`/api/problems${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<ProblemListResponse>(response), status: response.status };
}

export async function getProblem(slug: string): Promise<{
  data?: ProblemDetail;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch(`/api/problems/${slug}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<ProblemDetail>(response), status: response.status };
}

export type AttemptStatus = "in_progress" | "submitted" | "abandoned";

export type MistakeType =
  | "off_by_one"
  | "wrong_data_structure"
  | "missed_edge_case"
  | "incorrect_complexity"
  | "logic_error"
  | "unknown";

export type AttemptResponse = {
  id: string;
  problem_id: string;
  status: AttemptStatus;
  started_at: string;
  submitted_at: string | null;
  time_spent_seconds: number | null;
  hints_used_count: number;
  is_correct: boolean | null;
  mistake_type: MistakeType | null;
  code_text: string | null;
  client_attempt_id: string;
};

export type AttemptProblemDetail = {
  id: string;
  slug: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  prompt_md: string;
  hint_count: number;
  activity_kind?: ActivityKind;
  options?: QuizOption[] | null;
};

export type AttemptHintMeta = {
  id: string;
  ordinal: number;
};

export type AttemptEvent = {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  hint_body_md: string | null;
};

export type AttemptDetail = {
  attempt: AttemptResponse;
  problem: AttemptProblemDetail;
  events: AttemptEvent[];
  available_hints: AttemptHintMeta[];
};

export type AttemptListItem = {
  id: string;
  problem: {
    id: string;
    slug: string;
    title: string;
    difficulty: "easy" | "medium" | "hard";
    activity_kind?: ActivityKind;
  };
  status: AttemptStatus;
  started_at: string;
  submitted_at: string | null;
  time_spent_seconds: number | null;
  hints_used_count: number;
  is_correct: boolean | null;
  mistake_type: MistakeType | null;
};

export type AttemptListResponse = {
  items: AttemptListItem[];
  next_cursor: string | null;
  has_more: boolean;
};

async function postJson<T>(
  path: string,
  body?: unknown
): Promise<{ data?: T; error?: ApiErrorBody; status: number }> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<T>(response), status: response.status };
}

export async function startAttempt(input: {
  problem_id: string;
  client_attempt_id: string;
}): Promise<{ data?: AttemptResponse; error?: ApiErrorBody; status: number }> {
  return postJson<AttemptResponse>("/api/attempts", input);
}

export async function recordAttemptEvent(
  attemptId: string,
  input: { event_type: string; payload?: Record<string, unknown> }
): Promise<{ data?: AttemptEvent; error?: ApiErrorBody; status: number }> {
  return postJson<AttemptEvent>(`/api/attempts/${attemptId}/events`, input);
}

export async function submitAttempt(
  attemptId: string,
  input: {
    is_correct?: boolean;
    time_spent_seconds: number;
    mistake_type?: MistakeType;
    code_text?: string;
    selected_option?: string;
  }
): Promise<{ data?: SubmitAttemptResponse; error?: ApiErrorBody; status: number }> {
  return postJson<SubmitAttemptResponse>(`/api/attempts/${attemptId}/submit`, input);
}

export async function abandonAttempt(
  attemptId: string
): Promise<{ data?: AttemptResponse; error?: ApiErrorBody; status: number }> {
  return postJson<AttemptResponse>(`/api/attempts/${attemptId}/abandon`);
}

export async function listAttempts(filters?: {
  cursor?: string;
  limit?: number;
}): Promise<{ data?: AttemptListResponse; error?: ApiErrorBody; status: number }> {
  const query = buildQueryString({
    cursor: filters?.cursor,
    limit: filters?.limit,
  });
  const response = await fetch(`/api/attempts${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<AttemptListResponse>(response), status: response.status };
}

export async function getAttempt(
  attemptId: string
): Promise<{ data?: AttemptDetail; error?: ApiErrorBody; status: number }> {
  const response = await fetch(`/api/attempts/${attemptId}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<AttemptDetail>(response), status: response.status };
}

export type MasteryStatus = "insufficient" | "assessed";

export type EvidenceSummary = {
  id: string;
  evidence_type: string;
  polarity: string;
  strength: string;
  summary_text: string;
  skill_slug: string;
  skill_name: string;
  created_at: string;
};

export type SkillMasteryDelta = {
  skill_slug: string;
  skill_name: string;
  previous_score: string | null;
  new_score: string | null;
  delta: string | null;
  status: MasteryStatus;
  confidence: string;
  prerequisite_capped: boolean;
};

export type SubmitAssessmentOutcome = {
  evidence_items: EvidenceSummary[];
  mastery_deltas: SkillMasteryDelta[];
  recommendation: NextRecommendationResponse | null;
};

export type SubmitAttemptResponse = AttemptResponse & {
  assessment: SubmitAssessmentOutcome | null;
};

export type UserSkillMasteryItem = {
  skill_slug: string;
  skill_name: string;
  topic_slug: string | null;
  score: string | null;
  confidence: string;
  status: MasteryStatus;
  evidence_count: number;
  last_attempt_at: string | null;
};

export type UserMasteryResponse = {
  items: UserSkillMasteryItem[];
};

export type EvidenceTimelineItem = {
  id: string;
  evidence_type: string;
  polarity: string;
  strength: string;
  summary_text: string;
  created_at: string;
  attempt_id: string;
  details: Record<string, unknown>;
};

export type SnapshotItem = {
  score: string;
  confidence: string;
  computed_at: string;
  attempt_id: string;
};

export type UserSkillDetail = {
  slug: string;
  name: string;
  description: string;
  topic_slug: string | null;
  score: string | null;
  confidence: string;
  status: MasteryStatus;
  evidence_count: number;
  last_attempt_at: string | null;
  prerequisites: UserSkillMasteryItem[];
  dependents: UserSkillMasteryItem[];
  evidence_timeline: EvidenceTimelineItem[];
  snapshots: SnapshotItem[];
};

export async function getMyMastery(): Promise<{
  data?: UserMasteryResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/me/mastery", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<UserMasteryResponse>(response), status: response.status };
}

export async function getMySkillDetail(slug: string): Promise<{
  data?: UserSkillDetail;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch(`/api/me/skills/${slug}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<UserSkillDetail>(response), status: response.status };
}

export type RecommendationExplanation = {
  target_skill: string;
  reason_codes: string[];
  score_components: Record<string, number>;
  sentences: string[];
};

export type RecommendationProblemSummary = {
  id: string;
  slug: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  skills: ProblemSkillLink[];
  target_skill: ProblemSkillLink;
};

export type RecommendationItem = {
  id: string;
  rank: number;
  score: string;
  generated_at: string;
  source_attempt_id: string | null;
  problem: RecommendationProblemSummary;
  explanation: RecommendationExplanation;
};

export type RecommendationListResponse = {
  items: RecommendationItem[];
  target_skill: UserSkillMasteryItem | null;
  state: string;
  message: string | null;
};

export type NextRecommendationResponse = {
  recommendation: RecommendationItem | null;
  target_skill: UserSkillMasteryItem | null;
  state: string;
  message: string | null;
};

export async function getMyRecommendations(filters?: {
  limit?: number;
  target_skill?: string;
  refresh?: boolean;
}): Promise<{ data?: RecommendationListResponse; error?: ApiErrorBody; status: number }> {
  const query = buildQueryString({
    limit: filters?.limit,
    target_skill: filters?.target_skill,
    refresh: filters?.refresh ? "true" : undefined,
  });
  const response = await fetch(`/api/me/recommendations${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<RecommendationListResponse>(response), status: response.status };
}

export async function getNextRecommendation(filters?: {
  target_skill?: string;
  refresh?: boolean;
}): Promise<{ data?: NextRecommendationResponse; error?: ApiErrorBody; status: number }> {
  const query = buildQueryString({
    target_skill: filters?.target_skill,
    refresh: filters?.refresh ? "true" : undefined,
  });
  const response = await fetch(`/api/me/recommendations/next${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<NextRecommendationResponse>(response), status: response.status };
}

export async function getRecommendationDetail(id: string): Promise<{
  data?: RecommendationItem;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch(`/api/me/recommendations/${id}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<RecommendationItem>(response), status: response.status };
}

export type TargetProfileSummary = {
  slug: string;
  name: string;
  description: string;
  disclaimer: string;
};

export type TargetProfileListResponse = {
  items: TargetProfileSummary[];
  disclaimer: string;
};

export type LearnerTargetResponse = {
  profile: TargetProfileSummary | null;
  selected_at: string | null;
  disclaimer: string;
};

export async function listTargetProfiles(): Promise<{
  data?: TargetProfileListResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/target-profiles", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<TargetProfileListResponse>(response), status: response.status };
}

export async function getMyTarget(): Promise<{
  data?: LearnerTargetResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/me/target", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<LearnerTargetResponse>(response), status: response.status };
}

export async function setMyTarget(profileSlug: string): Promise<{
  data?: LearnerTargetResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/me/target", {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_slug: profileSlug }),
  });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<LearnerTargetResponse>(response), status: response.status };
}

export type SkillHighlight = {
  skill_slug: string;
  skill_name: string;
  score: number;
};

export type ReadinessDimensionItem = {
  key: string;
  display_name: string;
  status: string;
  score: number | null;
  confidence: number | null;
  coverage: number;
  assessed_count: number;
  in_scope_count: number;
  strongest_skills?: SkillHighlight[];
  weakest_actionable_skill?: SkillHighlight | null;
  target_min_score?: number | null;
  requirement_status?: string | null;
};

export type ReadinessGap = {
  dimension: string;
  skill_slug: string | null;
  skill_name: string | null;
  current: number | null;
  required: number;
  delta: number | null;
  status: string;
  severity: string;
  why: string;
  rank: number;
  is_critical?: boolean;
};

export type PlacementReadiness = {
  target: TargetProfileSummary | null;
  state: string;
  confidence: number | null;
  risk: string;
  dimensions: ReadinessDimensionItem[];
  blockers: ReadinessGap[];
  score: number | null;
  disclaimer: string;
  explanation?: string[];
  risk_disclaimer?: string;
};

export type GapListResponse = {
  items: ReadinessGap[];
  disclaimer: string;
};

export async function getMyReadiness(): Promise<{
  data?: PlacementReadiness;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/me/readiness", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<PlacementReadiness>(response), status: response.status };
}

export async function getMyGaps(): Promise<{
  data?: GapListResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const response = await fetch("/api/me/gaps", { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<GapListResponse>(response), status: response.status };
}

export type PlacementActionKind = "dsa_problem" | "cs_quiz" | "assess_dimension";

export type PlacementActionItem = {
  id: string;
  action_kind: PlacementActionKind;
  title: string;
  description: string;
  target_dimension: string;
  target_skill: { slug: string; name: string } | null;
  estimated_effort_minutes: number;
  score: string;
  rank: number;
  why: string[];
  reason_codes: string[];
  payload: Record<string, unknown>;
  generated_at: string;
};

export type NextPlacementActionResponse = {
  action: PlacementActionItem | null;
  state: string;
  message: string | null;
};

export type PlacementActionListResponse = {
  items: PlacementActionItem[];
  state: string;
  message: string | null;
};

export async function getNextPlacementAction(filters?: {
  refresh?: boolean;
}): Promise<{
  data?: NextPlacementActionResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const query = buildQueryString({
    refresh: filters?.refresh ? "true" : undefined,
  });
  const response = await fetch(`/api/me/actions/next${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<NextPlacementActionResponse>(response), status: response.status };
}

export type AssessmentPlanItem = {
  position: number;
  activity_kind: ActivityKind;
  problem_slug: string;
  problem_title: string;
  dimension: string;
  skill_slug: string;
  skill_name: string;
  estimated_minutes: number;
  difficulty: "easy" | "medium" | "hard";
};

export type AssessmentPlanResponse = {
  assessment_id: string | null;
  state: string;
  message: string | null;
  target: { slug: string; name: string } | null;
  total_items: number;
  items: AssessmentPlanItem[];
};

export async function getAssessmentPlan(filters?: { dimension?: string | null }): Promise<{
  data?: AssessmentPlanResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const query = buildQueryString({
    dimension: filters?.dimension ?? undefined,
  });
  const response = await fetch(`/api/me/assessment/plan${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<AssessmentPlanResponse>(response), status: response.status };
}

export async function getMyPlacementActions(filters?: {
  limit?: number;
  dimension?: string;
  refresh?: boolean;
}): Promise<{
  data?: PlacementActionListResponse;
  error?: ApiErrorBody;
  status: number;
}> {
  const query = buildQueryString({
    limit: filters?.limit,
    dimension: filters?.dimension,
    refresh: filters?.refresh ? "true" : undefined,
  });
  const response = await fetch(`/api/me/actions${query}`, { credentials: "include" });
  if (!response.ok) {
    return { error: await parseJson<ApiErrorBody>(response), status: response.status };
  }
  return { data: await parseJson<PlacementActionListResponse>(response), status: response.status };
}
