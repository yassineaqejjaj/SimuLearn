import { Clock, Mic } from "lucide-react";
import Link from "next/link";
import { Badge, Card, linkBtn } from "./ui";
import type { Scenario } from "@/lib/types";

export function ScenarioCard({ s, attempts = 0, reason }: { s: Scenario; attempts?: number; reason?: string }) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="teal">{s.category}</Badge>
        <Badge>{s.difficulty}</Badge>
        {attempts > 0 && <Badge tone="ok">{attempts === 1 ? "1 tentative" : `${attempts} tentatives`}</Badge>}
      </div>
      {reason && <p className="text-[13px] font-semibold text-action-ink">{reason}</p>}
      <h3 className="text-xl font-semibold tracking-[-.015em]">{s.title}</h3>
      <p className="text-[15px] leading-relaxed text-body">{s.description}</p>
      <p className="text-[13px] text-slate"><span className="font-semibold">Compétences : </span>{s.competencies.join(" · ")}</p>
      <div className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-2">
        <span className="flex items-center gap-4 text-sm text-body"><span className="inline-flex items-center gap-1.5"><Clock size={16} aria-hidden />{s.recommended_minutes} min</span><span className="inline-flex items-center gap-1.5"><Mic size={16} aria-hidden />Vocal</span></span>
        <Link href={`/scenarios/${s.id}`} className={linkBtn("primary")}>{attempts > 0 ? "Recommencer" : "Commencer"}</Link>
      </div>
    </Card>
  );
}
