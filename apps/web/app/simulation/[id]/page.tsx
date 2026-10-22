"use client";
import { useQuery } from "@tanstack/react-query";
import { Captions, Mic, MicOff, PhoneOff, SlidersHorizontal, TriangleAlert } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Persona } from "@/components/Persona";
import { Shell } from "@/components/Shell";
import { api, post } from "@/lib/api";
import { fmtMs } from "@/lib/format";
import type { Health, Scenario, SessionInfo } from "@/lib/types";
import { MIC_KEY } from "@/hooks/useMicLevel";
import { useVoiceSession } from "@/hooks/useVoiceSession";

const BARS = Array.from({ length: 41 }, (_, i) => ({ h: 24 + Math.round(Math.abs(Math.sin(i * 1.7)) * 72), d: ((i * 37) % 100) / 100 }));

export default function Room() {
  const { id } = useParams<{ id: string }>(); const router = useRouter();
  const session = useQuery({ queryKey: ["session", id], queryFn: () => api<SessionInfo>(`/api/simulations/${id}`) });
  const scenario = useQuery({ enabled: !!session.data, queryKey: ["scenario", session.data?.scenario_version_id], queryFn: () => api<Scenario>(`/api/scenarios/${session.data!.scenario_version_id}`) });
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health") });
  const mock = health.data?.voice_provider === "mock";
  const v = useVoiceSession(id, mock);
  const [trOpen, setTrOpen] = useState(false); const [draft, setDraft] = useState(""); const [now, setNow] = useState(Date.now());
  const audioDlg = useRef<HTMLDialogElement>(null); const [devs, setDevs] = useState<MediaDeviceInfo[]>([]); const [dev, setDev] = useState(""); const [micErr, setMicErr] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null); const started = useRef(false); const log = useRef<HTMLDivElement>(null);

  useEffect(() => { if (window.matchMedia("(min-width: 768px)").matches) setTrOpen(true); }, []);
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  // Démarrage automatique : l'utilisateur vient de cliquer « Démarrer la simulation » (micro autorisé à l'étape précédente).
  useEffect(() => { if (health.data && session.data?.status === "CREATED" && !started.current) { started.current = true; void v.start(); } }, [health.data, session.data, v]);
  useEffect(() => { if (v.connection === "ended") router.replace(`/results/${id}`); }, [v.connection, id, router]);
  useEffect(() => { log.current?.scrollTo({ top: log.current.scrollHeight }); }, [v.lines]);
  // Salle rechargée en cours de session : l'audio ne peut pas reprendre, on referme proprement puis on affiche les résultats.
  useEffect(() => {
    if (session.data && session.data.status !== "CREATED" && !started.current) {
      started.current = true;
      void post(`/api/simulations/${id}/end`).catch(() => undefined).finally(() => router.replace(`/results/${id}`));
    }
  }, [session.data, id, router]);

  const c = scenario.data?.character; const first = c?.name.split(" ")[0] ?? "Le patient";
  const elapsed = v.startedAt ? Math.max(0, now - v.startedAt) : 0;
  const state = v.error || v.connection === "error" ? "error" : v.connection === "idle" || v.connection === "connecting" ? "connecting" : v.connection === "closing" ? "closing"
    : v.connection === "lost" ? "lost" : v.muted ? "muted" : v.processing ? "processing" : v.speaking ? "speaking" : "listening";
  const COPY: Record<string, [string, string]> = {
    connecting: ["Connexion en cours…", "Un instant, le patient arrive."], closing: ["Fin de la simulation…", "Votre évaluation se prépare."],
    error: ["Connexion impossible", v.error ?? "Vérifiez votre connexion et réessayez."], lost: ["Connexion interrompue", "Votre échange est conservé."],
    muted: ["Microphone coupé", "Réactivez le micro pour parler."], processing: [`${first} réfléchit…`, "Un instant."],
    speaking: [`${first} vous répond…`, "Vous pouvez l'interrompre en parlant."], listening: [`${first} vous écoute`, "Parlez naturellement."],
  };
  const [label, hint] = COPY[state] as [string, string];
  const wave = state === "listening" ? "w-listen" : state === "speaking" ? "w-speak" : state === "muted" ? "w-muted" : "w-flat";
  const pill = v.muted ? ["Microphone coupé", "border-[#F2B866]/60 bg-[#F2B866]/15 text-[#FBE3BD]"] : mock ? ["Mode texte (mock)", "border-white/20 text-[#D5DEEE]"] : ["Microphone actif", "border-teal/50 bg-teal/15 text-[#9BE5DF]"];

  return (
    <Shell variant="bare">
      <div className="room relative flex h-full min-h-[560px] overflow-hidden bg-room text-white" style={{ backgroundImage: "radial-gradient(ellipse 620px 520px at 38% 42%, rgba(25,182,173,.10), rgba(11,22,48,0) 70%)" }}>
        <section className="flex min-w-0 flex-1 flex-col">
          <header className="flex min-h-[64px] flex-none items-center justify-between gap-3 px-4 md:h-[72px] md:px-8">
            <h1 className="min-w-0 truncate text-sm font-semibold md:text-[15px]">{scenario.data?.title ?? "Simulation"}</h1>
            <div className="flex flex-none items-center gap-3 md:gap-5"><p className="flex items-baseline gap-2"><span className="hidden text-[13px] text-[#B4C0D6] sm:inline">Temps écoulé</span><span className="num text-xl font-semibold" aria-label={`Temps écoulé ${fmtMs(elapsed)}`}>{fmtMs(elapsed)}</span></p>
              <span className={`whitespace-nowrap rounded-full border px-3 py-1.5 text-xs font-medium md:text-[13px] ${pill[1]}`}>{pill[0]}</span></div>
          </header>
          {state === "lost" && (
            <div role="status" className="mx-8 flex items-center gap-3 rounded-xl border border-[#E9A23B]/50 bg-[#E9A23B]/15 px-4 py-3 text-sm font-medium text-[#FBE3BD]"><TriangleAlert size={18} aria-hidden />
              <span className="flex-1">Connexion interrompue. Votre échange est conservé. Si elle ne revient pas, terminez la simulation pour obtenir votre évaluation.</span>
              <button className="min-h-10 rounded-[10px] border border-[#FBE3BD]/60 px-4 font-semibold" onClick={() => dialog.current?.showModal()}>Terminer</button></div>)}
          <div className="flex flex-1 flex-col items-center justify-center gap-2.5 overflow-y-auto pb-2">
            <div className="md:hidden"><Persona name={c?.name ?? "…"} size={104} live={state === "listening" || state === "speaking"} /></div>
            <div className="hidden md:block"><Persona name={c?.name ?? "…"} size={180} live={state === "listening" || state === "speaking"} /></div>
            <div className="text-center"><p className="text-2xl font-bold leading-tight tracking-[-.02em] md:text-[28px]">{c?.name ?? "Chargement…"}</p><p className="mt-1 text-[15px] text-[#B4C0D6]">{c ? `${c.role}, ${c.age} ans · personnage généré par IA` : ""}</p></div>
            <div role="status" aria-live="polite" className="mt-3 min-h-16 text-center"><p className="text-lg font-semibold">{label}</p><p className="mx-auto mt-1.5 max-w-[460px] text-[15px] leading-relaxed text-[#B4C0D6]">{hint}</p></div>
            {state === "processing" ? <div className="wave gap-3.5" aria-hidden><span className="dt" /><span className="dt" style={{ animationDelay: ".18s" }} /><span className="dt" style={{ animationDelay: ".36s" }} /></div>
              : !mock && <div className={`wave ${wave}`} aria-hidden>{BARS.map((b, i) => <span key={i} className="b" style={{ height: b.h, animationDelay: `${b.d}s` }} />)}</div>}
            {state === "error" && <button className="mt-2 min-h-11 rounded-xl bg-action px-6 font-semibold" onClick={() => { started.current = true; void v.start(); }}>Réessayer</button>}
            {mock && v.connection === "ready" && (
              <form className="mt-2 flex w-full max-w-lg gap-2 px-6" onSubmit={(e) => { e.preventDefault(); const t = draft.trim(); if (t) { void v.sendMock(t); setDraft(""); } }}>
                <label htmlFor="mock" className="sr-only">Votre réponse (mode mock)</label>
                <input id="mock" className="h-12 flex-1 rounded-xl bg-white px-4 text-night" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Ce que vous diriez au patient…" />
                <button className="min-h-12 rounded-xl bg-action px-5 font-semibold" type="submit">Envoyer</button></form>)}
          </div>
          <div className="flex min-h-24 flex-none flex-wrap items-center justify-center gap-x-5 gap-y-2 px-4 py-3 md:min-h-32 md:gap-7">
            {!mock && <button type="button" onClick={v.toggleMute} aria-pressed={v.muted} className="flex min-w-[72px] flex-col items-center gap-2 text-xs font-medium text-[#D5DEEE]">
              <span className={`grid h-14 w-14 place-items-center rounded-full border ${v.muted ? "border-[#F2B866] bg-[#F2B866]/20" : "border-white/20 hover:bg-white/15"}`}>{v.muted ? <MicOff size={22} aria-hidden /> : <Mic size={22} aria-hidden />}</span>{v.muted ? "Activer le micro" : "Couper le micro"}</button>}
            <button type="button" onClick={() => setTrOpen((o) => !o)} aria-pressed={trOpen} className="flex min-w-[72px] flex-col items-center gap-2 text-xs font-medium text-[#D5DEEE]">
              <span className={`grid h-14 w-14 place-items-center rounded-full border ${trOpen ? "border-[#8FB2FF] bg-[#8FB2FF]/20" : "border-white/20 hover:bg-white/15"}`}><Captions size={22} aria-hidden /></span>Transcription</button>
            {!mock && <button type="button" onClick={async () => { setMicErr(null); try { setDevs((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput")); setDev(sessionStorage.getItem(MIC_KEY) ?? ""); } catch { /* liste indisponible */ } audioDlg.current?.showModal(); }} className="flex min-w-[72px] flex-col items-center gap-2 text-xs font-medium text-[#D5DEEE]">
              <span className="grid h-14 w-14 place-items-center rounded-full border border-white/20 hover:bg-white/15"><SlidersHorizontal size={22} aria-hidden /></span>Audio</button>}
            <span className="mx-2 hidden h-12 w-px bg-white/20 sm:block" aria-hidden />
            <button type="button" onClick={() => dialog.current?.showModal()} disabled={v.connection === "closing"} className="inline-flex min-h-14 items-center gap-2.5 rounded-[28px] border border-white/40 px-5 text-[15px] md:px-6 font-semibold hover:bg-white/10 disabled:opacity-50"><PhoneOff size={20} aria-hidden />Terminer la simulation</button>
          </div>
        </section>
        {trOpen && (
          <aside aria-label="Transcription de la conversation" className="fixed inset-x-0 bottom-0 z-20 flex max-h-[62dvh] flex-col rounded-t-3xl border-t border-white/15 bg-[#13203d] shadow-2xl md:static md:max-h-none md:w-[400px] md:flex-none md:rounded-none md:border-l md:border-t-0 md:bg-white/[.04] md:shadow-none">
            <div className="flex items-center justify-between px-6 pb-3 pt-5"><h2 className="text-sm font-semibold">Transcription</h2>
              <button type="button" onClick={() => setTrOpen(false)} className="min-h-11 rounded-lg px-3 text-sm font-semibold text-[#B4C0D6] hover:bg-white/10 md:hidden">Fermer</button></div>
            <div ref={log} className="flex flex-1 flex-col gap-3 overflow-y-auto px-6 pb-4">
              {v.lines.length === 0 && <p className="text-sm text-[#B4C0D6]">La transcription apparaîtra ici. Elle est automatique et peut comporter des erreurs.</p>}
              {v.lines.map((l, i) => (
                <div key={i} className={`max-w-[92%] rounded-[14px] px-3.5 py-2.5 text-sm leading-relaxed ${l.speaker === "learner" ? "self-end rounded-br bg-action" : "self-start rounded-bl bg-white/10"}`}>
                  <p className="mb-0.5 text-xs font-semibold opacity-80">{l.speaker === "learner" ? "Vous" : c?.name} · {fmtMs(l.start_ms)}</p>{l.text}</div>))}
            </div>
            <p className="border-t border-white/10 px-6 py-3 text-xs text-[#B4C0D6]">Aucun score n'est affiché pendant la simulation. Vos résultats arrivent à la fin.</p>
          </aside>)}
        <dialog ref={audioDlg} aria-labelledby="audio-title" className="m-auto w-[min(440px,92vw)] rounded-3xl bg-white p-7 text-night backdrop:bg-black/60">
          <h2 id="audio-title" className="text-2xl font-bold tracking-[-.02em]">Réglages audio</h2>
          <label htmlFor="mic-sel" className="mt-5 block text-sm font-semibold">Microphone
            <select id="mic-sel" value={dev} onChange={async (e) => { setDev(e.target.value); setMicErr(null); try { await v.changeMic(e.target.value); } catch { setMicErr("Ce micro n'a pas pu être activé. Le précédent reste utilisé."); } }} className="mt-1.5 h-12 w-full rounded-xl border border-[#CBD5E1] bg-white px-3 font-normal">
              {devs.map((d, i) => <option key={d.deviceId || i} value={d.deviceId}>{d.label || `Microphone ${i + 1}`}</option>)}</select></label>
          <label htmlFor="vol" className="mt-4 block text-sm font-semibold">Volume du patient
            <input id="vol" type="range" min={0} max={1} step={0.05} value={v.volume} onChange={(e) => v.setVolume(Number(e.target.value))} className="mt-2 w-full accent-[#3867E8]" /></label>
          {micErr && <p role="alert" className="mt-3 text-sm text-red-800">{micErr}</p>}
          <button className="mt-6 min-h-12 w-full rounded-xl bg-action font-semibold text-white hover:bg-action-dark" onClick={() => audioDlg.current?.close()}>Fermer</button>
        </dialog>
        <dialog ref={dialog} aria-labelledby="end-title" className="m-auto w-[min(440px,92vw)] rounded-3xl bg-white p-7 text-night backdrop:bg-black/60">
          <h2 id="end-title" className="text-2xl font-bold tracking-[-.02em]">Terminer la simulation ?</h2>
          <p className="mt-2 text-[15px] leading-relaxed text-body">Votre échange sera enregistré et votre évaluation sera préparée. Vous ne pourrez pas reprendre cette session, mais vous pourrez recommencer la simulation.</p>
          <div className="mt-6 flex flex-col gap-3">
            <button className="min-h-12 rounded-xl bg-action font-semibold text-white hover:bg-action-dark" onClick={() => { dialog.current?.close(); void v.end(); }}>Terminer et consulter mes résultats</button>
            <button className="min-h-12 rounded-xl border border-[#CBD5E1] font-semibold" onClick={() => dialog.current?.close()} autoFocus>Continuer la simulation</button></div>
        </dialog>
      </div>
    </Shell>
  );
}
