"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Card, ErrorBox, PageTitle, Spinner, linkBtn } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDay, fmtLong, fmtMinutes } from "@/lib/format";
import { compare, isEvaluated, numberAttempts, sessionChip, type Verdict } from "@/lib/learner";
import { useHistory } from "@/lib/queries";
import type { Comparison } from "@/lib/types";

const TONE: Record<Verdict, "ok" | "bad" | "neutral" | "dashed"> = { improved: "ok", declined: "bad", stable: "neutral", not_comparable: "dashed" };
const TXT: Record<Verdict, string> = { improved: "En progrès", declined: "En recul", stable: "Stable", not_comparable: "Non comparable" };

export default function Progression() {
  const hist = useHistory();
  const done = useMemo(() => (hist.data ?? []).filter((s) => s.status === "COMPLETED"), [hist.data]);
  const n = useMemo(() => numberAttempts(hist.data ?? []), [hist.data]);
  const evaluated = useMemo(() => done.filter(isEvaluated).sort((a, b) => a.created_at.localeCompare(b.created_at)), [done]);
  const [a, setA] = useState(""); const [b, setB] = useState("");
  // Par défaut : les deux dernières tentatives évaluées d'un même scénario et d'une même grille.
  useEffect(() => {
    if (a || b || !evaluated.length) return;
    const last = evaluated[evaluated.length - 1]!; const prev = [...evaluated].reverse().find((s) => s !== last && s.scenario_id === last.scenario_id && s.framework_id === last.framework_id);
    if (prev) { setA(prev.id); setB(last.id); }
  }, [evaluated, a, b]);
  const sa = evaluated.find((s) => s.id === a); const sb = evaluated.find((s) => s.id === b);
  const same = !!sa && !!sb && sa.id !== sb.id && sa.framework_id === sb.framework_id;
  const serverCmp = useQuery({ enabled: same, queryKey: ["cmp", sa?.evaluation_id, sb?.evaluation_id], queryFn: () => api<Comparison>(`/api/compare?a=${sa!.evaluation_id}&b=${sb!.evaluation_id}`) });
  const rows = serverCmp.data?.competencies ?? [];
  const count = (v: Verdict) => rows.filter((r) => r.verdict === v).length;
  const names = (v: Verdict) => rows.filter((r) => r.verdict === v).map((r) => r.label.toLowerCase());
  const opt = (s: (typeof evaluated)[number]) => <option key={s.id} value={s.id}>{s.scenario_title} · tentative {n.get(s.id)} · {fmtDay(s.created_at)}</option>;
  void compare;
  return (
    <Shell>
      <PageTitle title="Ma progression" lead="Comparez vos tentatives et repérez ce qui progresse, comme ce qui demande encore de la pratique." />
      <ErrorBox error={hist.error ?? serverCmp.error} />
      {hist.isLoading && <Spinner />}
      {evaluated.length < 2 && !hist.isLoading && <Card><p className="text-[15px] leading-relaxed text-body">Réalisez au moins deux simulations évaluées du même scénario pour comparer vos tentatives.</p><Link href="/catalogue" className={`${linkBtn("primary")} mt-4`}>Voir les simulations</Link></Card>}
      {evaluated.length >= 2 && <>
        <section aria-label="Bilan" className="grid gap-5 md:grid-cols-3">
          {([["improved", "En progrès", "text-ok"], ["stable", "Stables", "text-night"], ["not_comparable", "Non comparable", "text-slate"]] as const).map(([v, t, color]) => (
            <Card key={v}><p className="text-sm font-semibold text-slate">{t}</p><p className={`num mt-1 text-4xl font-bold ${color}`}>{same ? count(v) : "—"} <span className="text-lg font-medium text-slate">compétences</span></p>
              <p className="mt-2 text-sm leading-relaxed text-body">{same && count(v) ? `${names(v).join(", ")}${v === "improved" ? " : au moins un niveau gagné." : v === "stable" ? " : niveau inchangé entre les deux tentatives." : " : pas évaluée dans les deux tentatives."}` : "—"}</p></Card>))}
        </section>
        <Card className="flex flex-col gap-5">
          <h2 className="text-xl font-semibold">Comparer deux tentatives</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {([["Tentative de départ", a, setA], ["Tentative à comparer", b, setB]] as const).map(([l, val, set]) => (
              <label key={l} className="text-sm font-semibold">{l}<select className="mt-1.5 h-12 w-full rounded-xl border border-[#CBD5E1] bg-white px-3 font-normal" value={val} onChange={(e) => set(e.target.value)}><option value="">Choisir…</option>{evaluated.map(opt)}</select></label>))}
          </div>
          {sa && sb && sa.id !== sb.id && !same && <p role="alert" className="rounded-xl bg-amber-soft p-3 text-sm text-amber-ink">Ces deux tentatives n'utilisent pas la même grille d'évaluation : leurs scores ne se comparent pas directement.</p>}
          {serverCmp.data && <div className="overflow-x-auto"><table className="w-full text-left text-[15px]"><caption className="sr-only">Évolution des scores par compétence</caption>
            <thead><tr className="border-b border-line text-sm text-slate"><th className="py-3 pr-4 font-semibold">Compétence</th><th className="font-semibold">Tentative {n.get(a)}</th><th className="font-semibold">Tentative {n.get(b)}</th><th className="font-semibold">Évolution</th></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.competency_id} className="border-b border-[#EDF1F6] last:border-0"><td className="py-3.5 pr-4 font-medium">{r.label}</td>
              <td className="num">{r.before ?? "Non évalué"}{r.before !== null && "/5"}</td><td className="num">{r.after ?? "Non évalué"}{r.after !== null && "/5"}</td>
              <td><Badge tone={TONE[r.verdict as Verdict]}>{TXT[r.verdict as Verdict]}{r.delta ? ` (${r.delta > 0 ? "+" : ""}${r.delta})` : ""}</Badge></td></tr>)}</tbody></table></div>}
          <p className="text-[13px] text-slate">{serverCmp.data?.note ?? "Seules les compétences évaluées avec les mêmes critères dans les deux tentatives sont comparées."} Évaluations générées par IA, à titre d'entraînement.</p>
          {sb && <div className="flex flex-wrap gap-3"><Link href={`/scenarios/${sb.scenario_version_id}`} className={linkBtn("primary")}>Recommencer cette simulation</Link><Link href={`/results/${sb.id}`} className={linkBtn("secondary")}>Voir le détail de la tentative {n.get(sb.id)}</Link></div>}
        </Card></>}
      <Card className="overflow-x-auto"><h2 id="historique" className="scroll-mt-8 text-xl font-semibold">Historique des simulations terminées</h2>
        <table className="mt-3 w-full text-left text-[15px]"><caption className="sr-only">Historique</caption>
          <thead><tr className="border-b border-line text-sm text-slate"><th className="py-3 pr-4 font-semibold">Simulation</th><th className="font-semibold">Date</th><th className="font-semibold">Durée</th><th className="font-semibold">Évaluation</th><th><span className="sr-only">Action</span></th></tr></thead>
          <tbody>{done.map((s) => { const chip = sessionChip(s); return (
            <tr key={s.id} className="border-b border-[#EDF1F6] last:border-0"><td className="py-3.5 pr-4"><p className="font-medium">{s.scenario_title}</p><p className="text-[13px] text-slate">Tentative {n.get(s.id)}</p></td>
              <td>{fmtLong(s.created_at)}</td><td>{fmtMinutes(s.duration_s)}</td><td><Badge tone={chip.tone}>{chip.text}</Badge></td>
              <td><Link className="font-semibold text-action-ink" href={`/results/${s.id}`}>Voir le détail</Link></td></tr>); })}</tbody></table>
        {done.length === 0 && !hist.isLoading && <p className="py-3 text-[15px] text-body">Aucune simulation terminée pour le moment.</p>}</Card>
    </Shell>
  );
}
