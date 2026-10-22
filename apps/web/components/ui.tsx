import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({ variant = "primary", className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  return (
    <button
      {...p}
      className={clsx(
        "inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border px-5 text-[15px] font-semibold transition active:scale-[.98] disabled:cursor-not-allowed disabled:bg-[#F1F4F9] disabled:text-[#6B7A90] disabled:active:scale-100",
        variant === "primary" && "border-transparent bg-action text-white hover:bg-action-dark",
        variant === "secondary" && "border-[#CBD5E1] bg-white text-night hover:bg-[#F1F4F9]",
        variant === "danger" && "border-transparent bg-red-700 text-white hover:bg-red-800",
        variant === "ghost" && "border-transparent bg-transparent text-action-ink hover:bg-action-soft",
        className,
      )}
    />
  );
}

/** Lien d'apparence bouton (navigation). */
export const linkBtn = (variant: "primary" | "secondary" | "ghost" = "primary") =>
  clsx("inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border px-5 text-[15px] font-semibold transition active:scale-[.98]",
    variant === "primary" && "border-transparent bg-action text-white hover:bg-action-dark",
    variant === "secondary" && "border-[#CBD5E1] bg-white text-night hover:bg-[#F1F4F9]",
    variant === "ghost" && "border-transparent text-action-ink hover:bg-action-soft");

export const Card = ({ children, className }: { children: ReactNode; className?: string }) => (
  <section className={clsx("rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(16,29,53,.04)]", className)}>{children}</section>
);

type Tone = "neutral" | "teal" | "ok" | "warn" | "bad" | "action" | "dashed";
export const Badge = ({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) => (
  <span className={clsx("inline-flex h-7 items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-[13px] font-medium",
    tone === "neutral" && "bg-chip text-[#2B3A55]", tone === "teal" && "bg-teal-soft text-teal-ink", tone === "ok" && "bg-ok-soft text-ok",
    tone === "warn" && "bg-amber-soft text-amber-ink", tone === "bad" && "bg-red-100 text-red-800", tone === "action" && "bg-action-soft text-action-ink",
    tone === "dashed" && "border border-dashed border-[#8896AB] bg-white text-body")}>{children}</span>
);

export const Eyebrow = ({ children }: { children: ReactNode }) => <p className="text-xs font-semibold uppercase tracking-[.08em] text-slate">{children}</p>;

export const ErrorBox = ({ error }: { error: unknown }) => error ? (
  <p role="alert" className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error instanceof Error ? error.message : String(error)}</p>
) : null;

export const Spinner = ({ label = "Chargement…" }: { label?: string }) => <p role="status" className="text-sm text-slate">{label}</p>;

export const PageTitle = ({ title, lead }: { title: string; lead?: string }) => (
  <header><h1 className="text-[32px] font-bold leading-tight tracking-[-.025em] text-night md:text-4xl">{title}</h1>{lead && <p className="mt-2 text-[17px] leading-relaxed text-body">{lead}</p>}</header>
);

export { fmtDate, fmtMs } from "@/lib/format";
