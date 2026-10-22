"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import { Badge, Card, ErrorBox, fmtDate } from "@/components/ui";
import { api } from "@/lib/api";

type Row = { id: string; learner: string; scenario_title: string; created_at: string; status: string; evaluation_id: string | null; review_status: string | null };

export default function Trainer() {
  const dash = useQuery({ queryKey: ["t-dash"], queryFn: () => api<{ learners: number; sessions: number; evaluations_to_review: number }>("/api/trainer/dashboard") });
  const sessions = useQuery({ queryKey: ["t-sessions"], queryFn: () => api<Row[]>("/api/trainer/sessions") });
  const learners = useQuery({ queryKey: ["t-learners"], queryFn: () => api<{ id: string; email: string; role: string }[]>("/api/trainer/learners") });
  const groups = useQuery({ queryKey: ["t-groups"], queryFn: () => api<{ id: string; name: string; members: number }[]>("/api/trainer/groups") });
  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-bold text-night">Espace formateur</h1>
        <Link href="/trainer/scenarios" className="rounded-xl bg-action px-4 py-2.5 text-sm font-semibold text-white hover:bg-action-dark">Gérer les scénarios</Link></div>
      <ErrorBox error={dash.error ?? sessions.error} />
      <div className="grid gap-4 md:grid-cols-3">
        <Card><p className="text-sm">Apprenants</p><p className="text-3xl font-bold">{dash.data?.learners ?? "…"}</p></Card>
        <Card><p className="text-sm">Sessions</p><p className="text-3xl font-bold">{dash.data?.sessions ?? "…"}</p></Card>
        <Card><p className="text-sm">Évaluations à relire</p><p className="text-3xl font-bold">{dash.data?.evaluations_to_review ?? "…"}</p></Card>
      </div>
      <h2 className="mb-2 mt-8 text-lg font-semibold">Sessions</h2>
      <Card className="overflow-x-auto p-0"><table className="w-full text-left text-sm"><caption className="sr-only">Sessions des apprenants</caption>
        <thead className="bg-surface"><tr><th className="p-3">Apprenant</th><th>Date</th><th>Scénario</th><th>Statut</th><th>Relecture</th><th /></tr></thead>
        <tbody>{sessions.data?.map((s) => <tr key={s.id} className="border-t border-line"><td className="p-3">{s.learner}</td><td>{fmtDate(s.created_at)}</td><td>{s.scenario_title}</td>
          <td><Badge>{s.status}</Badge></td><td>{s.review_status ?? "—"}</td>
          <td>{s.evaluation_id && <Link className="text-action-ink underline" href={`/trainer/evaluations/${s.evaluation_id}`}>Examiner</Link>}</td></tr>)}</tbody></table></Card>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <Card><h2 className="font-semibold">Apprenants</h2><ul className="mt-2 text-sm">{learners.data?.map((l) => <li key={l.id}>{l.email} <Badge>{l.role}</Badge></li>)}</ul></Card>
        <Card><h2 className="font-semibold">Groupes</h2>{groups.data?.length ? <ul className="mt-2 text-sm">{groups.data.map((g) => <li key={g.id}>{g.name} ({g.members})</li>)}</ul> : <p className="mt-2 text-sm text-slate">Aucun groupe (la gestion des groupes arrive après le MVP vocal).</p>}</Card>
      </div>
    </Shell>
  );
}
