import { describe, expect, it } from "vitest";
import { fmtMs, initials } from "./format";
import { compare, levelLabel, numberAttempts, recommend } from "./learner";
import type { Scenario, SessionInfo } from "./types";

const s = (id: string, day: number, sc = "A", status = "COMPLETED") => ({ id, scenario_id: sc, status, created_at: `2026-10-${day}T10:00:00Z` }) as SessionInfo;

describe("format", () => {
  it("formate les horodatages mm:ss", () => { expect(fmtMs(42000)).toBe("00:42"); expect(fmtMs(125000)).toBe("02:05"); });
  it("initiales", () => { expect(initials("Camille Dubois")).toBe("CD"); expect(initials("etudiant@ifsi.test")).toBe("ET"); });
});

describe("learner", () => {
  it("numérote les tentatives par scénario, ignore les sessions non terminées", () => {
    const m = numberAttempts([s("c", 20), s("a", 10), s("b", 15), s("x", 12, "B"), s("f", 11, "A", "FAILED")]);
    expect([m.get("a"), m.get("b"), m.get("c"), m.get("x"), m.get("f")]).toEqual([1, 2, 3, 1, undefined]);
  });
  it("compare : non observable => non comparable, jamais un delta inventé", () => {
    expect(compare(null, 3)).toEqual({ verdict: "not_comparable", delta: null });
    expect(compare(2, 3)).toEqual({ verdict: "improved", delta: 1 });
    expect(compare(3, 3).verdict).toBe("stable");
  });
  it("libellés de niveau", () => { expect(levelLabel(3)).toBe("À consolider"); expect(levelLabel(null)).toBe("Non évalué"); });
});

describe("recommend", () => {
  const sc = (id: string, comps: string[]) => ({ id: `v${id}`, scenario_id: id, competencies: comps }) as Scenario;
  const done = (scenario_id: string, score: number) => ({ id: "h", scenario_id, status: "COMPLETED", evaluation_id: "e", created_at: "2026-10-20T10:00:00Z",
    competencies: [{ id: "a", label: "Empathie", score }, { id: "b", label: "Clarté", score: 5 }] }) as SessionInfo;
  it("ne recommande que des scénarios jamais tentés, ceux qui travaillent la compétence faible en premier", () => {
    const r = recommend([sc("1", ["Clarté"]), sc("2", ["Empathie"]), sc("3", ["Clarté"])], [done("3", 2)]);
    expect(r.map((x) => x.scenario.scenario_id)).toEqual(["2", "1"]);
    expect(r[0]!.reason).toBe("Pour travailler : empathie");
  });
  it("sans évaluation : pas de raison inventée", () => {
    expect(recommend([sc("1", ["Clarté"])], [])[0]!.reason).toBe("Nouvelle situation à explorer");
  });
});
