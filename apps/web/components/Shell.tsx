"use client";
import { useQuery, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BookOpen, History, LayoutDashboard, LineChart, LogOut, UserRound, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { authMode, initAuth, isTrainer, login, logout } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Health } from "@/lib/types";

export function Providers({ children }: { children: ReactNode }) {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } }));
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

export const Logo = ({ dark = false, compact = false }: { dark?: boolean; compact?: boolean }) => (
  <span className="flex items-center gap-3">
    <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden><rect width="40" height="40" rx="12" fill={dark ? "#fff" : "#101D35"} /><path d="M27.5 13.5A10 10 0 1 0 27.5 26.5" fill="none" stroke="#19B6AD" strokeWidth="3" strokeLinecap="round" /><circle cx="28" cy="20" r="3" fill={dark ? "#101D35" : "#fff"} /></svg>
    {!compact && <span className={`text-[22px] font-bold tracking-[-.02em] ${dark ? "text-white" : "text-night"}`}>SimuLearn</span>}
  </span>
);

const NAV = [
  { href: "/", label: "Tableau de bord", icon: LayoutDashboard }, { href: "/catalogue", label: "Simulations", icon: BookOpen },
  { href: "/progression", label: "Ma progression", icon: LineChart }, { href: "/progression#historique", label: "Historique", icon: History },
  { href: "/profile", label: "Mon profil", icon: UserRound },
];

/** variant "app" : rail de navigation ; "bare" : plein écran sans cadre (salle, préparation). */
export function Shell({ children, variant = "app" }: { children: ReactNode; variant?: "app" | "bare" }) {
  const router = useRouter(); const path = usePathname();
  const [ready, setReady] = useState(false); const [trainer, setTrainer] = useState(false);
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health") });

  useEffect(() => {
    void initAuth().then((ok) => {
      if (!ok) { if (authMode === "dev") router.replace("/login"); else login(); return; }
      setTrainer(isTrainer()); setReady(true);
    });
  }, [router]);

  if (!ready) return <main className="grid min-h-screen place-items-center bg-surface text-slate" role="status">Connexion…</main>;
  const missing = [...(health.data?.missing_config.voice ?? []), ...(health.data?.missing_config.evaluation ?? [])];
  const banners = (
    <>
      {health.data?.warning && <p className="bg-amber-soft px-4 py-2 text-center text-sm text-amber-ink" role="status">{health.data.warning}</p>}
      {missing.length > 0 && <p className="bg-red-100 px-4 py-2 text-center text-sm text-red-900" role="alert">Configuration manquante côté serveur : {missing.join(", ")}.</p>}
    </>
  );
  if (variant === "bare") return <div className="flex h-dvh flex-col">{banners}<div className="min-h-0 flex-1 overflow-y-auto">{children}</div></div>;

  const items = trainer ? [...NAV, { href: "/trainer", label: "Formateur", icon: Users }] : NAV;
  return (
    <div className="flex min-h-screen flex-wrap bg-surface">
      <nav aria-label="Navigation principale" className="flex w-full flex-row items-stretch justify-between gap-0.5 bg-night p-1.5 md:sticky md:top-0 md:h-screen md:w-[104px] md:flex-none md:flex-col md:justify-start md:py-5">
        <Link href="/" aria-label="SimuLearn, accueil" className="mb-3 hidden md:block"><Logo dark compact /></Link>
        {items.map(({ href, label, icon: Icon }) => {
          const here = href === "/" ? path === "/" : path === href.split("#")[0] && !href.includes("#");
          return (
            <Link key={href} href={href} aria-current={here ? "page" : undefined}
              className={`flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-0.5 py-2 text-center text-[11px] font-medium leading-tight hover:bg-white/10 hover:text-white md:w-[88px] md:flex-none md:gap-1.5 md:px-1 md:py-2.5 md:text-xs ${here ? "bg-white/15 text-white" : "text-[#B9C5DB]"}`}>
              <Icon size={22} aria-hidden /><span className="max-w-full break-words">{label}</span>
            </Link>
          );
        })}
        <button onClick={logout} className="flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-0.5 py-2 text-center text-[11px] font-medium leading-tight text-[#B9C5DB] hover:bg-white/10 hover:text-white md:mt-auto md:w-[88px] md:flex-none md:gap-1.5 md:px-1 md:py-2.5 md:text-xs"><LogOut size={22} aria-hidden />Déconnexion</button>
      </nav>
      <div className="min-w-0 flex-1 basis-[560px]">
        {banners}
        <main className="mx-auto flex max-w-[1160px] flex-col gap-7 px-6 pb-16 pt-8 md:px-14 md:pt-10">{children}</main>
      </div>
    </div>
  );
}

