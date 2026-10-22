export type Scenario = {
  id: string; scenario_id: string; version: number; title: string; description: string; target_profession: string; category: string;
  difficulty: string; recommended_minutes: number; context: string; learner_role: string; objectives: string[];
  character: { name: string; role: string; age: number }; competencies: string[];
};
export type SessionInfo = {
  id: string; scenario_version_id: string; scenario_title: string; status: string; provider: string; created_at: string;
  started_at: string | null; ended_at: string | null; end_reason: string | null; max_duration_seconds: number;
  transcript_complete: boolean; evaluation_id?: string | null; evaluation_status?: string | null;
  framework_id?: string | null; scenario_id: string; review_status?: string | null; duration_s?: number | null;
  competencies?: { id: string; label: string; score: number | null }[];
};
export type Me = { email: string; display_name: string; role: string; organization: string };
export type Evidence = { message_id: string; quote: string; start_ms: number; end_ms: number };
export type CompetencyResult = {
  competency_id: string; label: string; score: number | null; status: "scored" | "not_observable"; confidence: number | null;
  justification: string; strengths: string[]; improvements: string[]; recommendation: string; evidence: Evidence[];
  trainer_correction: { score: number | null; comment: string } | null;
};
export type Evaluation = {
  id: string; session_id: string; status: string; provider: string; model: string; warnings: string[]; error: string | null;
  trainer_review_status: string; disclaimer: string; competencies: CompetencyResult[];
  overall_feedback: { summary: string; strengths: string[]; improvements: string[]; next_steps: string[] } | null;
  framework: { id: string; key: string; version: number };
  trainer_comments: { comment: string; created_at: string }[]; raw_output?: unknown;
};
export type Message = { id: string; speaker: "learner" | "character"; text: string; start_ms: number; end_ms: number; reliability: string; note: string | null };
export type Health = { status: string; voice_provider: string; evaluation_provider: string; auth: string; warning: string | null;
  missing_config: { voice: string[]; evaluation: string[] } };
export type Comparison = {
  framework: { key: string; version: number }; improved: string[]; to_work_on: string[]; note: string;
  before: { date: string; session_id: string }; after: { date: string; session_id: string };
  competencies: { competency_id: string; label: string; before: number | null; after: number | null; delta: number | null; verdict: string }[];
};
