"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CircleCheck, Lightbulb } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Pips } from "@/components/Pips";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, ErrorBox, Spinner, linkBtn } from "@/components/ui";
import { api, post } from "@/lib/api";
import { fmtLong, fmtMs } from "@/lib/format";
import { levelLabel, numberAttempts } from "@/lib/learner";
import { useHistory } from "@/lib/queries";
import type { Evaluation, SessionInfo } from "@/lib/types";

type Pending = { status: "pending" | "none"; session_status: string };

export default function Results() {
  const { id } = useParams<{ id: string }>(); const router = useRouter();
  const session = useQuery({ queryKey: ["session", id], queryFn: () => api<SessionInfo>(`/api/simulations/${id}`) });
  const ev = useQuery({
    queryKey: ["eval", id], queryFn: () => api<Evaluation | Pending>(`/api/simulations/${id}/evaluation`),
    refetchInterval: (q) => { const d = q.state.data as Partial<Evaluation> | undefined; return d && "competencies" in d && d.status !== "pending" ? false : 2500; },
  });
  const hist = useHistory();
  const retry = useMutation({ mutationFn: () => post(`/api/simulations/${id}/evaluate`), onSuccess: () => void ev.refetch() });
  const e = ev.data && "competencies" in ev.data ? ev.data : null;
  const me = hist.data?.find((h) => h.id === id);
  const attempt = hist.data ? numberAttempts(hist.data).get(id) : undefined;
  const scored = e?.competencies.filter((c) => (c.trainer_correction?.score ?? c.score) !== null).length ?? 0;
  const reviewed = e && e.trainer_review_status !== "pending";

  return (
    <Shell>
      <header><h1 className="text-4xl font-bold leading-tight tracking-[-.025em]">Votre simulation est terminée</h1><p className="mt-2 text-[17px] text-body">Découvrez vos points forts et les compétences à améliorer.</p></header>
      <ErrorBox error={ev.error} />
      {!e && !ev.error && <Card><Spinner label="Analyse de votre conversation en cours…" />
        {session.data?.status === "FAILED" && <p role="alert" className="mt-2 text-sm text-red-800">La session a été interrompue avant toute parole : aucune évaluation n'est disponible.</p>}</Card>}
      {e?.status === "failed" && (
        <Card className="flex flex-col items-start gap-3"><p role="alert" className="text-red-800">L'évaluation n'a pas pu être produite : {e.error}</p>
          <Button onClick={() => retry.mutate()} disabled={retry.isPending}>Relancer l'évaluation</Button></Card>)}
      {e && e.status !== "failed" && <>
        <Card className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm text-slate">Résumé de la session</p><h2 className="text-xl font-semibold">{session.data?.scenario_title}</h2></div>
          <dl className="flex flex-wrap gap-8 text-sm"><div><dt className="text-slate">Date</dt><dd className="font-semibold">{session.data ? fmtLong(session.data.created_at) : ""}{attempt ? ` · tentative ${attempt}` : ""}</dd></div>
            <div><dt className="text-slate">Durée</dt><dd className="font-semibold">{me?.duration_s ? `${Math.floor(me.duration_s / 60)} min ${me.duration_s % 60} s` : "—"}</dd></div>
            <div><dt className="text-slate">Compétences évaluées</dt><dd className="font-semibold">{scored} sur {e.competencies.length}</dd></div></dl>
        </Card>
        <div className="flex flex-wrap items-center gap-3"><Badge tone={reviewed ? "ok" : "action"}>{e.provider === "mock" ? "Évaluation de développement (non fiable)" : `Évaluation générée par IA · ${reviewed ? "relue par un formateur" : "en attente de relecture"}`}</Badge>
          <p className="text-sm text-body">{e.disclaimer} Votre formateur peut la relire et l'ajuster.</p></div>
        {session.data && !session.data.transcript_complete && <p role="status" className="rounded-xl bg-amber-soft p-3 text-sm text-amber-ink">La connexion a été interrompue : la fin de votre échange est peut-être incomplète, l'évaluation en tient compte.</p>}
        {e.warnings.length > 0 && <p role="status" className="rounded-xl bg-amber-soft p-3 text-sm text-amber-ink">Certains éléments n'ont pas pu être vérifiés ({e.warnings.length}) ; ils ne sont pas pris en compte.</p>}
        <Card><h2 className="text-xl font-semibold">Retour général</h2><p className="mt-2 text-[17px] leading-relaxed text-body">{e.overall_feedback?.summary}</p>
          <p className="mt-3 text-sm text-slate">Chaque compétence est évaluée séparément : il n'y a pas de note globale.</p></Card>
        <section aria-labelledby="comp"><h2 id="comp" className="mb-4 text-2xl font-semibold tracking-[-.015em]">Vos compétences</h2>
          <div className="grid gap-5 lg:grid-cols-2">{e.competencies.map((c) => {
            const shown = c.trainer_correction?.score ?? c.score;
            return shown === null ? (
              <div key={c.competency_id} className="flex flex-col gap-3 rounded-2xl border border-dashed border-[#8896AB] bg-[#FAFBFD] p-5">
                <div className="flex items-baseline justify-between"><h3 className="font-semibold">{c.label}</h3><span className="font-semibold text-body">Non évalué</span></div>
                <Pips score={null} label={c.label} /><p className="text-[13px] text-slate">Preuves insuffisantes dans cet échange : aucune note n'est attribuée.</p></div>
            ) : (
              <Card key={c.competency_id} className="flex flex-col gap-3 p-5">
                <div className="flex items-baseline justify-between"><h3 className="font-semibold">{c.label}</h3><span className="num font-semibold">{shown}/5</span></div>
                <Pips score={shown} label={c.label} /><p className="text-[13px] font-medium text-slate">{levelLabel(shown)}{c.trainer_correction?.score != null && " · corrigé par le formateur"}</p>
                {c.trainer_correction?.comment && <p className="text-sm text-action-ink">Formateur : {c.trainer_correction.comment}</p>}
                <p className="text-[15px] leading-relaxed text-body">{c.justification}</p>
                {c.evidence.map((x) => <blockquote key={x.message_id + x.quote} className="rounded-xl bg-surface p-3 text-sm italic leading-relaxed"><span className="mb-1 block text-xs font-semibold not-italic text-slate">Extrait · Vous · {fmtMs(x.start_ms)}</span>« {x.quote} »</blockquote>)}
                {c.recommendation && <p className="text-sm leading-relaxed"><strong>Pour progresser : </strong>{c.recommendation}</p>}
              </Card>);
          })}</div></section>
        {((e.overall_feedback?.strengths.length ?? 0) > 0 || (e.overall_feedback?.improvements.length ?? 0) > 0) && <div className="grid gap-5 md:grid-cols-2">
          {(e.overall_feedback?.strengths.length ?? 0) > 0 && <Card><h2 className="text-xl font-semibold">Vos points forts</h2><ul className="mt-3 space-y-2.5">{e.overall_feedback!.strengths.map((t) => <li key={t} className="flex gap-2.5 text-[15px] leading-relaxed"><CircleCheck size={20} className="mt-0.5 flex-none text-ok" aria-hidden />{t}</li>)}</ul></Card>}
          {(e.overall_feedback?.improvements.length ?? 0) > 0 && <Card><h2 className="text-xl font-semibold">À améliorer</h2><ul className="mt-3 space-y-2.5">{e.overall_feedback!.improvements.map((t) => <li key={t} className="flex gap-2.5 text-[15px] leading-relaxed"><Lightbulb size={20} className="mt-0.5 flex-none text-amber-ink" aria-hidden />{t}</li>)}</ul></Card>}</div>}
        {(e.overall_feedback?.next_steps?.length ?? 0) > 0 && <Card><h2 className="text-xl font-semibold">Conseils pour la prochaine simulation</h2>
          <ol className="mt-4 space-y-3">{e.overall_feedback!.next_steps.map((t, i) => <li key={t} className="flex gap-3"><span className="grid h-8 w-8 flex-none place-items-center rounded-full bg-action-soft text-sm font-bold text-action-ink">{i + 1}</span><p className="pt-1 text-[15px] leading-relaxed">{t}</p></li>)}</ol></Card>}
        {e.trainer_comments.length > 0 && <Card><h2 className="text-xl font-semibold">Commentaires du formateur</h2>{e.trainer_comments.map((c) => <p key={c.created_at} className="mt-2 text-[15px]">{c.comment}</p>)}</Card>}
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => session.data && router.push(`/preparation/${session.data.scenario_version_id}`)} disabled={!session.data}>Recommencer cette simulation</Button>
          <Link href="/progression" className={linkBtn("secondary")}>Voir ma progression</Link>
          <Link href="/" className={linkBtn("ghost")}>Retour au tableau de bord</Link></div>
      </>}
    </Shell>
  );
}
