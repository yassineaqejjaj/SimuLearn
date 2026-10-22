import type { Scenario, SessionInfo } from "./types";

/** Libellé qualitatif d'un score 1-5 (aide à la lecture, pas une note globale). */
export function levelLabel(score: number | null): string {
  if (score === null) return "Non évalué";
  return score <= 2 ? "À travailler" : score === 3 ? "À consolider" : score === 4 ? "Solide" : "Très solide";
}

export const isEvaluated = (s: SessionInfo) => !!s.evaluation_id && (s.competencies?.length ?? 0) > 0;

/** Numérote les tentatives par scénario, de la plus ancienne (1) à la plus récente. */
export function numberAttempts(sessions: SessionInfo[]): Map<string, number> {
  const out = new Map<string, number>();
  const bucket = new Map<string, SessionInfo[]>();
  for (const s of sessions.filter((x) => x.status === "COMPLETED")) bucket.set(s.scenario_id, [...(bucket.get(s.scenario_id) ?? []), s]);
  for (const list of bucket.values()) list.sort((a, b) => a.created_at.localeCompare(b.created_at)).forEach((s, i) => out.set(s.id, i + 1));
  return out;
}

export type Verdict = "improved" | "declined" | "stable" | "not_comparable";
export function compare(a: number | null, b: number | null): { verdict: Verdict; delta: number | null } {
  if (a === null || b === null) return { verdict: "not_comparable", delta: null };
  const d = b - a;
  return { verdict: d > 0 ? "improved" : d < 0 ? "declined" : "stable", delta: d };
}

export function sessionChip(s: SessionInfo): { text: string; tone: "ok" | "action" | "warn" | "bad" | "neutral" } {
  if (s.status === "FAILED") return { text: "Interrompue", tone: "bad" };
  if (s.status !== "COMPLETED") return { text: "En cours", tone: "neutral" };
  if (s.evaluation_status === "failed") return { text: "Évaluation à relancer", tone: "warn" };
  if (!s.evaluation_id || s.evaluation_status === "pending") return { text: "Évaluation en cours", tone: "neutral" };
  return s.review_status === "pending" ? { text: "Évaluation à vérifier", tone: "action" } : { text: "Évaluation prête", tone: "ok" };
}

export type Recommendation = { scenario: Scenario; reason: string };

/**
 * Recommandation par la compétence la plus faible de la dernière évaluation.
 * Priorité : scénarios jamais tentés qui travaillent cette compétence, puis les autres jamais tentés.
 * Sans évaluation, aucune raison n'est inventée.
 */
export function recommend(scenarios: Scenario[], history: SessionInfo[]): Recommendation[] {
  const done = history.filter((h) => h.status === "COMPLETED");
  const tried = new Set(done.map((h) => h.scenario_id));
  const last = done.find(isEvaluated);
  const scored = (last?.competencies ?? []).filter((c) => c.score !== null);
  const weakest = [...scored].sort((a, b) => a.score! - b.score!)[0];
  return scenarios
    .filter((s) => !tried.has(s.scenario_id))
    .map((s) => ({ scenario: s, reason: weakest && s.competencies.includes(weakest.label) ? `Pour travailler : ${weakest.label.toLowerCase()}` : "Nouvelle situation à explorer" }))
    .sort((a, b) => Number(b.reason.startsWith("Pour")) - Number(a.reason.startsWith("Pour")));
}
