"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Clock, ClipboardCheck, Info, Mic, MicOff } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Logo, Shell } from "@/components/Shell";
import { Badge, Button, Card, ErrorBox, Eyebrow, Spinner } from "@/components/ui";
import { useMicTest } from "@/hooks/useMicLevel";
import { api, post } from "@/lib/api";
import type { Health, Scenario, SessionInfo } from "@/lib/types";

export default function Preparation() {
  const { id } = useParams<{ id: string }>(); const router = useRouter();
  const sc = useQuery({ queryKey: ["scenario", id], queryFn: () => api<Scenario>(`/api/scenarios/${id}`) });
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health") });
  const mic = useMicTest(); const mock = health.data?.voice_provider === "mock";
  const start = useMutation({ mutationFn: () => post<SessionInfo>("/api/simulations", { scenario_version_id: id }), onSuccess: (s) => { mic.stop(); router.push(`/simulation/${s.id}`); } });
  const s = sc.data; const canStart = (mic.status === "ready" || mock) && !start.isPending;
  const facts = [[Clock, "Durée estimée", `${s?.recommended_minutes ?? "…"} min`], [Mic, "Interaction", "Conversation vocale"], [Mic, "Matériel", "Microphone"], [ClipboardCheck, "Évaluation", "Après la session"]] as const;
  return (
    <Shell variant="bare">
      <div className="min-h-full bg-surface">
        <header className="flex items-center justify-between px-6 py-5 md:px-14"><Logo /><Link href={s ? `/scenarios/${s.id}` : "/catalogue"} className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-action-ink"><ArrowLeft size={16} aria-hidden />Retour aux simulations</Link></header>
        <main className="mx-auto grid max-w-[1160px] gap-6 px-6 pb-16 md:px-14 lg:grid-cols-2">
          <div className="flex flex-col gap-5">
            <header><Eyebrow>Avant de commencer</Eyebrow><h1 className="mt-2 text-4xl font-bold leading-tight tracking-[-.025em]">{s?.title ?? <Spinner />}</h1></header>
            {s && <><Card className="flex flex-col gap-4">
              <div><h2 className="text-sm font-semibold text-slate">Situation</h2><p className="mt-1 text-[15px] leading-relaxed">{s.context}</p></div>
              <div><h2 className="text-sm font-semibold text-slate">Votre rôle</h2><p className="mt-1 text-[15px] leading-relaxed">{s.learner_role}</p></div>
              <div><h2 className="text-sm font-semibold text-slate">Votre objectif</h2><ul className="mt-1 list-disc space-y-1 pl-5 text-[15px] leading-relaxed">{s.objectives.slice(0, 4).map((o) => <li key={o}>{o}</li>)}</ul></div>
            </Card>
            <dl className="grid grid-cols-2 gap-3">{facts.map(([Icon, k, v]) => <div key={k} className="flex items-center gap-3 rounded-2xl border border-line bg-white p-4"><Icon size={20} className="text-action" aria-hidden /><div><dt className="text-[13px] text-slate">{k}</dt><dd className="font-semibold">{v}</dd></div></div>)}</dl></>}
            <ErrorBox error={sc.error} />
          </div>
          <div className="flex flex-col gap-5">
            <Card className="flex flex-col gap-4">
              <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Votre microphone</h2>
                <Badge tone={mic.status === "ready" ? "ok" : mic.status === "denied" || mic.status === "unavailable" ? "bad" : "warn"}>{mic.status === "ready" ? "Prêt" : mic.status === "denied" ? "Accès refusé" : mic.status === "unavailable" ? "Introuvable" : "Autorisation requise"}</Badge></div>
              {mock && <p className="rounded-xl bg-amber-soft p-3 text-sm text-amber-ink">Mode mock du serveur : la voix est remplacée par une saisie texte, le micro n'est pas nécessaire.</p>}
              {(mic.status === "idle" || mic.status === "requesting") && <><p className="text-[15px] leading-relaxed text-body">SimuLearn a besoin de votre microphone pour que vous puissiez parler au patient. Votre navigateur vous demandera votre accord.</p>
                <Button variant="secondary" onClick={() => void mic.request()} disabled={mic.status === "requesting"}><Mic size={18} aria-hidden />Autoriser le microphone</Button></>}
              {mic.status === "denied" && <p role="alert" className="text-[15px] text-red-800">Le navigateur a refusé l'accès au micro. Autorisez-le depuis l'icône de cadenas de la barre d'adresse, puis réessayez.</p>}
              {mic.status === "unavailable" && <p role="alert" className="text-[15px] text-red-800">Aucun microphone utilisable n'a été trouvé. Branchez un casque ou un micro, puis réessayez.</p>}
              {(mic.status === "denied" || mic.status === "unavailable") && <Button variant="secondary" onClick={() => void mic.request()}><MicOff size={18} aria-hidden />Réessayer</Button>}
              {mic.status === "ready" && <>
                <label className="text-sm font-semibold" htmlFor="dev">Microphone utilisé
                  <select id="dev" className="mt-1.5 h-12 w-full rounded-xl border border-[#CBD5E1] bg-white px-3 font-normal" value={mic.deviceId} onChange={(e) => void mic.request(e.target.value)}>
                    {mic.devices.map((d, i) => <option key={d.deviceId || i} value={d.deviceId}>{d.label || `Microphone ${i + 1}`}</option>)}</select></label>
                <div><p className="text-sm font-semibold">Dites quelques mots pour tester</p>
                  <div className="mt-2 h-3 overflow-hidden rounded-full bg-[#DCE3EE]" role="meter" aria-label="Niveau sonore" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(mic.level * 100)}><div className="h-3 rounded-full bg-teal transition-[width] duration-75" style={{ width: `${mic.level * 100}%` }} /></div></div></>}
            </Card>
            <div className="flex gap-3 rounded-2xl bg-action-soft p-4 text-sm leading-relaxed text-[#1E3A8A]"><Info size={20} className="mt-0.5 flex-none" aria-hidden />
              <p><strong>Un entraînement, pas une situation réelle.</strong> {s?.character.name ?? "Le patient"} est un personnage généré par IA ; la situation est fictive. Votre voix est transmise en direct à OpenAI pour la conversation et transcrite ; SimuLearn n'enregistre pas l'audio. La transcription est conservée pour votre évaluation (réalisée avec Anthropic).</p></div>
            <Link href="/profile" className="-mt-2 inline-flex min-h-11 items-center self-start text-sm font-semibold text-action-ink underline">Gérer mes données</Link>
            <ErrorBox error={start.error} />
            <Button className="min-h-[52px] w-full text-base" disabled={!canStart} onClick={() => start.mutate()}>Démarrer la simulation</Button>
            {!canStart && !start.isPending && <p className="-mt-2 text-center text-sm text-slate">Autorisez le microphone pour commencer.</p>}
          </div>
        </main>
      </div>
    </Shell>
  );
}
