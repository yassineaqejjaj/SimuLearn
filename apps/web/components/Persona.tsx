import { initials } from "@/lib/format";

/** Portraits illustrés de la maquette, par personnage. Sans illustration : monogramme (pas d'avatar 3D au MVP). */
const PORTRAITS: Record<string, React.ReactNode> = {
  "Marc Laurent": (
    <svg viewBox="0 0 200 200" className="h-full w-full" aria-hidden>
      <rect width="200" height="200" fill="#DCE6F5" /><path d="M14 200c4-36 34-56 86-56s82 20 86 56z" fill="#3B4A63" /><path d="M80 146l20 28 20-28z" fill="#E8EDF5" />
      <rect x="88" y="118" width="24" height="34" rx="10" fill="#D49A78" /><ellipse cx="65" cy="96" rx="6" ry="10" fill="#D49A78" /><ellipse cx="135" cy="96" rx="6" ry="10" fill="#D49A78" />
      <ellipse cx="100" cy="92" rx="35" ry="42" fill="#E4B08E" /><path d="M64 88C60 56 78 44 100 44s40 12 36 44c-3-12-8-22-18-26-12 6-38 6-54 26z" fill="#B4BBC7" />
      <path d="M79 80l16 5M121 80l-16 5" stroke="#8C95A3" strokeWidth="3.5" fill="none" strokeLinecap="round" /><ellipse cx="88" cy="95" rx="3.6" ry="4" fill="#26324A" /><ellipse cx="112" cy="95" rx="3.6" ry="4" fill="#26324A" />
      <path d="M100 97v13q-5 4-8 1" stroke="#C48A68" strokeWidth="2.5" fill="none" strokeLinecap="round" /><path d="M88 124q12-6 24 0" stroke="#A8665A" strokeWidth="3" fill="none" strokeLinecap="round" />
    </svg>
  ),
};

export function Persona({ name, size = 176, live = false }: { name: string; size?: number; live?: boolean }) {
  const portrait = PORTRAITS[name];
  return (
    <div role="img" aria-label={portrait ? `Portrait illustré de ${name}, personnage simulé` : `Portrait de ${name}`} className="relative grid place-items-center" style={{ width: size * 1.6, height: size * 1.6 }}>
      <span aria-hidden className={`absolute inset-0 rounded-full border-2 border-teal/50 ${live ? "ring-live" : ""}`} />
      <span aria-hidden className="absolute rounded-full border border-white/15" style={{ inset: size * 0.14 }} />
      <span className="grid place-items-center overflow-hidden rounded-full bg-[#DCE6F5] font-bold text-night" style={{ width: size, height: size, fontSize: size * 0.3 }}>{portrait ?? initials(name)}</span>
    </div>
  );
}
