"use client";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { Button, Card, ErrorBox, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { useMe } from "@/lib/queries";
import { useQueryClient } from "@tanstack/react-query";

export default function Profile() {
  const me = useMe(); const qc = useQueryClient(); const [confirm, setConfirm] = useState(false);
  const exp = useMutation({ mutationFn: () => api<unknown>("/api/me/export"), onSuccess: (d) => {
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" })); a.download = "simulearn-mes-donnees.json"; a.click(); URL.revokeObjectURL(a.href); } });
  const del = useMutation({ mutationFn: () => api<void>("/api/me/data", { method: "DELETE" }), onSuccess: () => { setConfirm(false); void qc.invalidateQueries(); } });
  return (
    <Shell>
      <PageTitle title="Mon profil" lead="Vos informations et la gestion de vos données." />
      <Card><dl className="grid gap-4 sm:grid-cols-3 text-[15px]"><div><dt className="text-sm text-slate">Nom</dt><dd className="font-semibold">{me.data?.display_name || "—"}</dd></div><div><dt className="text-sm text-slate">E-mail</dt><dd className="font-semibold">{me.data?.email}</dd></div><div><dt className="text-sm text-slate">Établissement</dt><dd className="font-semibold">{me.data?.organization}</dd></div></dl></Card>
      <Card className="flex flex-col gap-4"><h2 className="text-xl font-semibold">Mes données</h2>
        <p className="text-[15px] leading-relaxed text-body">SimuLearn n'enregistre pas l'audio. Sont conservées : la transcription de vos simulations, leurs évaluations et les corrections de votre formateur. La voix est traitée en direct par OpenAI et l'évaluation est produite avec Anthropic.</p>
        <ErrorBox error={exp.error ?? del.error} />
        <div className="flex flex-wrap gap-3"><Button variant="secondary" onClick={() => exp.mutate()} disabled={exp.isPending}>Exporter mes données</Button>
          {!confirm ? <Button variant="secondary" onClick={() => setConfirm(true)}>Supprimer mes transcriptions et évaluations</Button> : <>
            <Button variant="danger" onClick={() => del.mutate()} disabled={del.isPending}>Oui, tout supprimer définitivement</Button><Button variant="ghost" onClick={() => setConfirm(false)}>Annuler</Button></>}</div>
        {del.isSuccess && <p role="status" className="text-sm text-ok">Vos transcriptions et évaluations ont été supprimées.</p>}</Card>
    </Shell>
  );
}
