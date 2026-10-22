"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { MIC_KEY } from "./useMicLevel";
import { post } from "@/lib/api";

export type Connection = "idle" | "connecting" | "ready" | "lost" | "closing" | "ended" | "error";
export type LiveLine = { speaker: "learner" | "character"; text: string; start_ms: number };

/** Connexion WebRTC à GPT-Live. Chaque état vient d'un événement réel (data channel, état WebRTC, niveau audio distant). */
export function useVoiceSession(sessionId: string, mock: boolean) {
  const [connection, setConnection] = useState<Connection>("idle");
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<LiveLine[]>([]);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const pc = useRef<RTCPeerConnection | null>(null); const stream = useRef<MediaStream | null>(null);
  const raf = useRef(0); const t0 = useRef(0); const actx = useRef<AudioContext | null>(null);
  const audioEl = useRef<HTMLAudioElement | null>(null); const mutedRef = useRef(false);
  const [volume, setVolumeState] = useState(1);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(raf.current); stream.current?.getTracks().forEach((t) => t.stop());
    pc.current?.close(); void actx.current?.close(); pc.current = null; stream.current = null; actx.current = null; setSpeaking(false);
  }, []);
  useEffect(() => cleanup, [cleanup]);

  const addLine = (speaker: LiveLine["speaker"], delta: string, start_ms: number) =>
    setLines((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.speaker === speaker && start_ms - last.start_ms < 15000) return [...prev.slice(0, -1), { ...last, text: last.text + delta }];
      return [...prev, { speaker, text: delta, start_ms }];
    });

  const onEvent = (raw: string) => {
    let ev: { type: string; delta?: string; start_ms?: number; error?: { code?: string } };
    try { ev = JSON.parse(raw); } catch { return; }
    switch (ev.type) {
      case "session.started": t0.current = Date.now(); setConnection("ready"); setStartedAt(Date.now()); break;
      case "session.input_transcript.delta": addLine("learner", ev.delta ?? "", ev.start_ms ?? 0); break;
      case "session.output_transcript.delta": setProcessing(false); addLine("character", ev.delta ?? "", ev.start_ms ?? 0); break;
      case "session.delegation.created": setProcessing(true); break;
      case "session.closed": setConnection("ended"); break;
      case "error": void post(`/api/simulations/${sessionId}/client-events`, { type: "client.error", detail: { code: ev.error?.code } }).catch(() => undefined); break;
    }
  };

  const start = useCallback(async () => {
    setError(null); setConnection("connecting");
    try {
      if (mock) { // pas de voix en mode mock : la salle propose une saisie texte
        await post(`/api/simulations/${sessionId}/connect`, {}); t0.current = Date.now(); setConnection("ready"); setStartedAt(Date.now()); return;
      }
      let deviceId: string | undefined; try { deviceId = sessionStorage.getItem(MIC_KEY) || undefined; } catch { /* non disponible */ }
      const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, ...(deviceId ? { deviceId: { ideal: deviceId } } : {}) } });
      stream.current = mic;
      const conn = new RTCPeerConnection(); pc.current = conn;
      mic.getTracks().forEach((t) => conn.addTrack(t, mic));
      const el = new Audio(); el.autoplay = true; el.volume = volume; audioEl.current = el;
      conn.ontrack = (e) => {
        el.srcObject = e.streams[0] ?? null;
        const ctx = new AudioContext(); actx.current = ctx; const an = ctx.createAnalyser(); an.fftSize = 512;
        ctx.createMediaStreamSource(e.streams[0]!).connect(an);
        const buf = new Uint8Array(an.frequencyBinCount);
        const tick = () => { an.getByteFrequencyData(buf); setSpeaking(buf.reduce((a, b) => a + b, 0) / buf.length > 6); raf.current = requestAnimationFrame(tick); };
        tick();
      };
      const dc = conn.createDataChannel("oai-events"); // label imposé par la doc GPT-Live
      dc.onmessage = (m) => onEvent(String(m.data));
      conn.onconnectionstatechange = () => {
        void post(`/api/simulations/${sessionId}/client-events`, { type: "client.connection_state", detail: { state: conn.connectionState } }).catch(() => undefined);
        if (conn.connectionState === "failed" || conn.connectionState === "disconnected") setConnection((c) => (c === "ready" ? "lost" : c));
        else if (conn.connectionState === "connected") setConnection((c) => (c === "lost" ? "ready" : c));
      };
      await conn.setLocalDescription(await conn.createOffer());
      await new Promise<void>((res) => {
        if (conn.iceGatheringState === "complete") return res();
        conn.onicegatheringstatechange = () => conn.iceGatheringState === "complete" && res();
      });
      const { sdp } = await post<{ sdp: string }>(`/api/simulations/${sessionId}/connect`, { sdp: conn.localDescription?.sdp });
      await conn.setRemoteDescription({ type: "answer", sdp });
      // « prêt » n'est affiché qu'à la réception de session.started
    } catch (e) {
      cleanup(); setError(e instanceof Error ? e.message : "Connexion impossible."); setConnection("error");
    }
  }, [sessionId, mock, cleanup]);

  const setVolume = useCallback((v: number) => { setVolumeState(v); if (audioEl.current) audioEl.current.volume = v; }, []);

  /** Change de micro en cours de session sans renégocier la connexion (RTCRtpSender.replaceTrack). */
  const changeMic = useCallback(async (deviceId: string) => {
    const next = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, deviceId: { exact: deviceId } } });
    const track = next.getAudioTracks()[0]; if (!track) return;
    track.enabled = !mutedRef.current;
    const sender = pc.current?.getSenders().find((x) => x.track?.kind === "audio");
    await sender?.replaceTrack(track);
    stream.current?.getTracks().forEach((t) => t.stop()); stream.current = next;
    try { sessionStorage.setItem(MIC_KEY, deviceId); } catch { /* stockage indisponible */ }
  }, []);

  const toggleMute = useCallback(() => {
    const next = !muted; setMuted(next); mutedRef.current = next;
    stream.current?.getAudioTracks().forEach((t) => (t.enabled = !next));
    void post(`/api/simulations/${sessionId}/client-events`, { type: next ? "client.mic_muted" : "client.mic_unmuted" }).catch(() => undefined);
  }, [muted, sessionId]);

  const end = useCallback(async () => {
    setConnection("closing");
    try { await post(`/api/simulations/${sessionId}/end`); } finally { cleanup(); setConnection("ended"); }
  }, [sessionId, cleanup]);

  const sendMock = useCallback(async (text: string) => {
    addLine("learner", text, Date.now() - t0.current);
    const r = await post<{ character_reply: string }>(`/api/simulations/${sessionId}/mock-turn`, { text });
    addLine("character", r.character_reply, Date.now() - t0.current + 1);
  }, [sessionId]);

  return { connection, muted, speaking, processing, error, lines, startedAt, start, toggleMute, end, sendMock, volume, setVolume, changeMic };
}
