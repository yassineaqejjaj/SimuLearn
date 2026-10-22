"use client";
import { useCallback, useEffect, useRef, useState } from "react";

export const MIC_KEY = "simulearn.mic-device";
export type MicStatus = "idle" | "requesting" | "ready" | "denied" | "unavailable";

/** Test du micro : niveau sonore RÉEL (AnalyserNode), jamais simulé. */
export function useMicTest() {
  const [status, setStatus] = useState<MicStatus>("idle");
  const [level, setLevel] = useState(0);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const stream = useRef<MediaStream | null>(null); const raf = useRef(0); const ctx = useRef<AudioContext | null>(null);

  const stop = useCallback(() => {
    cancelAnimationFrame(raf.current); stream.current?.getTracks().forEach((t) => t.stop()); void ctx.current?.close(); stream.current = null; ctx.current = null; setLevel(0);
  }, []);
  useEffect(() => stop, [stop]);

  const request = useCallback(async (id?: string) => {
    stop(); setStatus("requesting");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: id ? { deviceId: { exact: id } } : true });
      stream.current = s;
      const used = s.getAudioTracks()[0]?.getSettings().deviceId ?? id ?? "";
      setDeviceId(used); try { sessionStorage.setItem(MIC_KEY, used); } catch { /* stockage indisponible */ }
      setDevices((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput"));
      const c = new AudioContext(); ctx.current = c; const an = c.createAnalyser(); an.fftSize = 512;
      c.createMediaStreamSource(s).connect(an); const buf = new Uint8Array(an.frequencyBinCount);
      const tick = () => { an.getByteTimeDomainData(buf); let peak = 0; for (const v of buf) peak = Math.max(peak, Math.abs(v - 128)); setLevel(Math.min(1, peak / 64)); raf.current = requestAnimationFrame(tick); };
      tick(); setStatus("ready");
    } catch (e) {
      setStatus(e instanceof DOMException && (e.name === "NotAllowedError" || e.name === "SecurityError") ? "denied" : "unavailable");
    }
  }, [stop]);

  return { status, level, devices, deviceId, request, stop };
}
