"use client";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Clock, Mic } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Persona } from "@/components/Persona";
import { Shell } from "@/components/Shell";
import { Badge, Card, ErrorBox, Eyebrow, Spinner, linkBtn } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtLong, fmtMinutes } from "@/lib/format";
import { numberAttempts, sessionChip } from "@/lib/learner";
import { useHistory } from "@/lib/queries";
import type { Scenario } from "@/lib/types";

const STEPS = [["Préparez-vous", "Lisez la situation et vérifiez votre microphone."], ["Parlez naturellement", "Le patient réagit à ce que vous dites, comme en service."], ["Consultez vos résultats", "Un retour détaillé, appuyé sur des extraits de l'échange."]];

export default function ScenarioPage() {
  const { id } = useParams<{ id: string }>();
  const q = useQuery({ queryKey: ["scenario", id], queryFn: () => api<Scenario>(`/api/scenarios/${id}`) });
  const hist = useHistory(); const s = q.data;
  const mine = (hist.data ?? []).filter((h) => s && h.scenario_id === s.scenario_id && h.status === "COMPLETED");
  const n = numberAttempts(hist.data ?? []);
  const evaluated = mine.filter((h) => h.evaluation_id && h.competencies?.length);
  return (
    <Shell>
      <Link href="/catalogue" className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-action-ink"><ArrowLeft size={16} aria-hidden />Retour aux simulations</Link>
      {q.isLoading && <Spinner />}<ErrorBox error={q.error} />
      {s && (
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <div className="flex flex-col gap-6">
            <header className="flex flex-col items-start gap-3">
              <div className="flex flex-wrap gap-2"><Badge tone="teal">{s.category}</Badge><Badge>{s.difficulty}</Badge><Badge><Clock size={13} aria-hidden />{s.recommended_minutes} min</Badge><Badge><Mic size={13} aria-hidden />Conversation vocale</Badge></div>
              <h1 className="text-4xl font-bold leading-tight tracking-[-.025em]">{s.title}</h1>
              <p className="max-w-2xl text-[17px] leading-relaxed text-body">{s.description}</p>
            </header>
            <Card><Eyebrow>Compétences travaillées</Eyebrow><ul className="mt-3 flex flex-wrap gap-2">{s.competencies.map((c) => <li key={c}><Badge>{c}</Badge></li>)}</ul></Card>
            <Card><h2 className="text-xl font-semibold">Comment ça se passe</h2>
              <ol className="mt-4 grid gap-5 md:grid-cols-3">{STEPS.map(([t, d], i) => <li key={t} className="flex gap-3"><span className="grid h-8 w-8 flex-none place-items-center rounded-full bg-action-soft text-sm font-bold text-action-ink">{i + 1}</span><div><p className="font-semibold">{t}</p><p className="mt-1 text-sm text-body">{d}</p></div></li>)}</ol></Card>
            <Card><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Vos tentatives</h2>
              {evaluated.length >= 2 && <Link href="/progression" className="text-sm font-semibold text-action-ink">Comparer</Link>}</div>
              {mine.length === 0 ? <p className="mt-3 text-[15px] text-body">Pas encore de tentative. Lancez-vous : il n'y a aucun risque de se tromper.</p> : (
                <ul className="mt-2">{mine.map((h) => { const chip = sessionChip(h); return (
                  <li key={h.id} className="flex flex-wrap items-center gap-4 border-t border-[#EDF1F6] py-3.5 first:border-t-0"><div className="flex-1"><p className="font-semibold">Tentative {n.get(h.id)}</p><p className="text-[13px] text-slate">{fmtLong(h.created_at)}{h.duration_s != null ? ` · ${fmtMinutes(h.duration_s)}` : ""}</p></div>
                    <Badge tone={chip.tone}>{chip.text}</Badge><Link href={`/results/${h.id}`} className="text-sm font-semibold text-action-ink">Voir</Link></li>); })}</ul>)}</Card>
          </div>
          <aside className="flex flex-col gap-4 lg:sticky lg:top-8 lg:self-start">
            <Card className="flex flex-col items-center gap-4 text-center">
              <div className="-my-6 rounded-full bg-night"><Persona name={s.character.name} size={96} /></div>
              <div><p className="text-lg font-semibold">{s.character.name}</p><p className="text-sm text-slate">{s.character.role}, {s.character.age} ans</p></div>
              <p className="text-[13px] leading-relaxed text-body">{s.character.name.split(" ")[0]} est un personnage généré par IA. La situation est fictive et ne représente aucun patient réel.</p>
              <dl className="grid w-full grid-cols-2 gap-3 text-left text-sm"><div><dt className="text-slate">Durée</dt><dd className="font-semibold">{s.recommended_minutes} min</dd></div><div><dt className="text-slate">Format</dt><dd className="font-semibold">Vocal</dd></div><div><dt className="text-slate">Matériel</dt><dd className="font-semibold">Microphone</dd></div><div><dt className="text-slate">Évaluation</dt><dd className="font-semibold">Après la session</dd></div></dl>
              <Link href={`/preparation/${s.id}`} className={`${linkBtn("primary")} w-full`}>Se préparer</Link>
            </Card>
          </aside>
        </div>
      )}
    </Shell>
  );
}
