"use client";
import { ArrowRight, Clock, Mic, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Persona } from "@/components/Persona";
import { Shell } from "@/components/Shell";
import { Badge, Card, ErrorBox, linkBtn } from "@/components/ui";
import { fmtDay, fmtMinutes, initials } from "@/lib/format";
import { compare, isEvaluated, levelLabel, numberAttempts, recommend, sessionChip } from "@/lib/learner";
import { ScenarioCard } from "@/components/ScenarioCard";
import { useHistory, useMe, useScenarios } from "@/lib/queries";

export default function Dashboard() {
  const sc = useScenarios(); const hist = useHistory(); const me = useMe();
  const done = (hist.data ?? []).filter((s) => s.status === "COMPLETED");
  const evaluated = done.filter(isEvaluated);
  const last = evaluated[0]; const prev = last && evaluated.find((s) => s !== last && s.framework_id === last.framework_id);
  const totalSeconds = done.reduce((a, s) => a + (s.duration_s ?? 0), 0);
  const worked = new Set(evaluated.flatMap((s) => (s.competencies ?? []).filter((c) => c.score !== null).map((c) => c.id)));
  const total = last?.competencies?.length;
  const scored = (last?.competencies ?? []).filter((c) => c.score !== null);
  const best = [...scored].sort((a, b) => b.score! - a.score!)[0]; const weak = [...scored].sort((a, b) => a.score! - b.score!)[0];
  const gains = prev && last ? (last.competencies ?? []).map((c) => ({ c, ...compare(prev.competencies?.find((p) => p.id === c.id)?.score ?? null, c.score), from: prev.competencies?.find((p) => p.id === c.id)?.score })).filter((g) => g.verdict === "improved") : [];
  const gain = gains.sort((a, b) => b.delta! - a.delta!)[0];
  const n = numberAttempts(hist.data ?? []);
  const recs = recommend(sc.data ?? [], hist.data ?? []);
  const featured = recs[0]?.scenario ?? sc.data?.[0];
  return (
    <Shell>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><h1 className="text-4xl font-bold leading-tight tracking-[-.025em]">Bonjour, prêt à vous entraîner ?</h1><p className="mt-2 text-[17px] text-body">Développez vos compétences grâce à des mises en situation interactives.</p></div>
        {me.data && <div className="flex items-center gap-3"><span aria-hidden className="grid h-11 w-11 place-items-center rounded-full bg-action-soft text-[15px] font-semibold text-action-ink">{initials(me.data.display_name || me.data.email)}</span>
          <div><p className="font-semibold">{me.data.display_name || me.data.email}</p><p className="text-[13px] text-slate">{me.data.organization}</p></div></div>}
      </header>
      <ErrorBox error={sc.error ?? hist.error} />
      {featured && (
        <section aria-label="Simulation à la une" className="grid items-center gap-8 rounded-3xl bg-night p-8 text-white md:grid-cols-2 md:p-12">
          <div className="flex flex-col items-start gap-4">
            <span className="inline-flex h-7 items-center rounded-full bg-white/10 px-3 text-[13px] font-medium">{featured.category}</span>
            <h2 className="text-4xl font-bold leading-[1.1] tracking-[-.03em]">{featured.title}</h2>
            <p className="max-w-[480px] text-[17px] leading-relaxed text-[#C7D2E6]">{featured.description}</p>
            <p className="flex flex-wrap gap-5 text-sm font-medium text-[#DCE4F2]"><span className="inline-flex items-center gap-2"><Clock size={16} aria-hidden />{featured.recommended_minutes} min</span><span>{featured.difficulty}</span><span className="inline-flex items-center gap-2"><Mic size={16} aria-hidden />Conversation vocale</span></p>
            <Link href={`/scenarios/${featured.id}`} className={`${linkBtn("primary")} mt-1 min-h-[52px] px-7 text-base`}>Commencer la simulation <ArrowRight size={18} aria-hidden /></Link>
          </div>
          <div className="flex flex-col items-center gap-2 text-center"><Persona name={featured.character.name} size={150} />
            <p className="font-semibold">{featured.character.name}</p><p className="text-[13px] text-[#B4C0D6]">{featured.character.role} · personnage généré par IA</p></div>
        </section>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="flex flex-col gap-5">
          <h2 className="text-xl font-semibold">Votre progression</h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-5">
            <div><dd className="num text-[34px] font-bold leading-none">{hist.isLoading ? "…" : done.length}</dd><dt className="mt-1.5 text-sm text-slate">Simulations terminées</dt></div>
            <div><dd className="num text-[34px] font-bold leading-none">{fmtMinutes(totalSeconds)}</dd><dt className="mt-1.5 text-sm text-slate">Temps de pratique</dt></div>
            <div><dd className="num text-[34px] font-bold leading-none">{worked.size}{total ? <span className="text-lg font-medium text-slate"> sur {total}</span> : null}</dd><dt className="mt-1.5 text-sm text-slate">Compétences évaluées</dt></div>
            <div><dd className="flex items-center gap-1.5 text-[34px] font-bold leading-none text-teal-ink">{gain ? <><TrendingUp size={26} aria-hidden />+{gain.delta}</> : "—"}</dd>
              <dt className="mt-1.5 text-sm text-slate">{gain ? `${gain.c.label}, de ${gain.from} à ${gain.c.score} sur 5` : "Progression visible dès 2 tentatives"}</dt></div>
          </dl>
        </Card>
        <Card className="flex flex-col gap-3">
          <h2 className="text-xl font-semibold">Dernière évaluation</h2>
          {last ? (<>
            <p className="font-semibold">{last.scenario_title} · tentative {n.get(last.id)}</p>
            <p className="text-[15px] leading-relaxed text-body">{fmtDay(last.created_at)}{best && ` · Point fort : ${best.label.toLowerCase()} (${best.score}/5)`}{weak && weak !== best && ` · À travailler : ${weak.label.toLowerCase()} (${weak.score}/5, ${levelLabel(weak.score).toLowerCase()})`}</p>
            <Link href={`/results/${last.id}`} className={`${linkBtn("secondary")} mt-auto self-start`}>Consulter mes résultats</Link>
          </>) : <p className="text-[15px] text-body">Aucune évaluation pour l'instant. Terminez une simulation pour recevoir votre premier retour.</p>}
        </Card>
      </div>
      {recs.length > 1 && <section aria-labelledby="reco"><h2 id="reco" className="mb-3 text-xl font-semibold">Recommandé pour vous</h2>
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{recs.slice(1, 4).map((r) => <ScenarioCard key={r.scenario.id} s={r.scenario} reason={r.reason} />)}</div></section>}
      <Card>
        <div className="mb-2 flex items-center justify-between"><h2 className="text-xl font-semibold">Simulations récentes</h2><Link href="/progression#historique" className="inline-flex min-h-11 items-center text-sm font-semibold text-action-ink">Tout l'historique</Link></div>
        {done.length === 0 && !hist.isLoading && <p className="py-3 text-[15px] text-body">Vos simulations terminées apparaîtront ici.</p>}
        <ul>{(hist.data ?? []).slice(0, 3).map((s) => { const chip = sessionChip(s); return (
          <li key={s.id} className="flex flex-wrap items-center gap-4 border-t border-[#EDF1F6] py-3.5 first:border-t-0">
            <div className="min-w-0 flex-1"><p className="font-semibold">{s.scenario_title}</p><p className="text-[13px] text-slate">{fmtDay(s.created_at)}{s.duration_s != null ? ` · ${fmtMinutes(s.duration_s)}` : ""}</p></div>
            <Badge tone={chip.tone}>{chip.text}</Badge>
            {s.status === "COMPLETED" && <Link href={`/results/${s.id}`} className="text-sm font-semibold text-action-ink">Voir</Link>}
          </li>); })}</ul>
      </Card>
      <div className="flex flex-col items-center gap-2 text-center"><p className="text-sm text-slate">Vous pouvez refaire chaque simulation autant de fois que nécessaire. Vos résultats vous aident à progresser.</p>
        <Link href="/catalogue" className={linkBtn("ghost")}>Voir toutes les simulations</Link></div>
    </Shell>
  );
}
