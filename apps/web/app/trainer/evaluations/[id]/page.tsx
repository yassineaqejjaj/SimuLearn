"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, ErrorBox, Spinner, fmtMs } from "@/components/ui";
import { api, post } from "@/lib/api";
import type { Evaluation } from "@/lib/types";

export default function TrainerEval() {
  const { id } = useParams<{ id: string }>(); const qc = useQueryClient();
  const q = useQuery({ queryKey: ["t-eval", id], queryFn: () => api<Evaluation>(`/api/trainer/evaluations/${id}`) });
  const [draft, setDraft] = useState<Record<string, { score: string; comment: string }>>({}); const [general, setGeneral] = useState("");
  const save = useMutation({ mutationFn: (b: object) => post(`/api/trainer/evaluations/${id}/reviews`, b), onSuccess: () => void qc.invalidateQueries({ queryKey: ["t-eval", id] }) });
  const e = q.data;
  return (
    <Shell>
      <h1 className="mb-1 text-2xl font-bold text-night">Examen de l'évaluation</h1>
      {q.isLoading && <Spinner />}<ErrorBox error={q.error ?? save.error} />
      {e && <div className="space-y-4">
        <p className="text-sm">Produite par {e.provider} ({e.model || "—"}) · statut de relecture : <Badge>{e.trainer_review_status}</Badge> · la sortie initiale est conservée, vos corrections s'y ajoutent.</p>
        {e.competencies.map((c) => { const d = draft[c.competency_id] ?? { score: "", comment: "" }; return (
          <Card key={c.competency_id} className="space-y-2">
            <h2 className="font-semibold">{c.label} — {c.score ?? "non observable"}{c.trainer_correction?.score ? ` → corrigé : ${c.trainer_correction.score}` : ""}</h2>
            <p className="text-sm">{c.justification}</p>
            {c.evidence.map((x) => <blockquote key={x.message_id + x.quote} className="border-l-4 border-action pl-3 text-sm italic">« {x.quote} » ({fmtMs(x.start_ms)})</blockquote>)}
            <div className="flex flex-wrap items-end gap-2">
              <label className="text-sm">Score corrigé<select className="ml-2 rounded border p-1.5" value={d.score} onChange={(ev) => setDraft({ ...draft, [c.competency_id]: { ...d, score: ev.target.value } })}><option value="">—</option>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></label>
              <label className="flex-1 text-sm">Commentaire<input className="ml-2 w-full rounded border p-1.5" value={d.comment} onChange={(ev) => setDraft({ ...draft, [c.competency_id]: { ...d, comment: ev.target.value } })} /></label>
              <Button variant="secondary" disabled={!d.score && !d.comment} onClick={() => save.mutate({ competency_key: c.competency_id, corrected_score: d.score ? Number(d.score) : null, comment: d.comment })}>Enregistrer</Button>
            </div></Card>); })}
        <Card className="space-y-2"><h2 className="font-semibold">Commentaire général</h2>
          <textarea className="w-full rounded border p-2" rows={3} value={general} onChange={(ev) => setGeneral(ev.target.value)} aria-label="Commentaire général" />
          <Button disabled={!general} onClick={() => { save.mutate({ comment: general }); setGeneral(""); }}>Ajouter le commentaire</Button></Card>
      </div>}
    </Shell>
  );
}
