export const fmtDate = (iso: string) => new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
export const fmtDay = (iso: string) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
export const fmtLong = (iso: string) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
export const fmtMs = (ms: number) => `${String(Math.floor(ms / 60000)).padStart(2, "0")}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
export const fmtDuration = (s: number | null | undefined) => (s == null ? "—" : s < 60 ? `${s} s` : `${Math.round(s / 60)} min`);
export function initials(name: string): string {
  const parts = (name.split("@")[0] ?? "").split(/[\s._-]+/).filter(Boolean);
  const out = parts.length > 1 ? parts.slice(0, 2).map((p) => p[0]!).join("") : (parts[0] ?? "").slice(0, 2);
  return out.toUpperCase();
}
/** Durée courte lisible : « < 1 min » plutôt que « 0 min » pour une session de quelques secondes. */
export const fmtMinutes = (s: number | null | undefined) => (s == null ? "—" : s < 60 ? "< 1 min" : `${Math.round(s / 60)} min`);
