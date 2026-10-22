"use client";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { ScenarioCard } from "@/components/ScenarioCard";
import { ErrorBox, PageTitle, Spinner } from "@/components/ui";
import { useHistory, useScenarios } from "@/lib/queries";

const norm = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

export default function Catalogue() {
  const sc = useScenarios(); const hist = useHistory();
  const [q, setQ] = useState(""); const [cat, setCat] = useState("");
  const cats = useMemo(() => [...new Set((sc.data ?? []).map((s) => s.category))].sort(), [sc.data]);
  const shown = useMemo(() => (sc.data ?? []).filter((s) => (!cat || s.category === cat) && norm([s.title, s.description, ...s.competencies].join(" ")).includes(norm(q))), [sc.data, q, cat]);
  const attempts = (id: string) => hist.data?.filter((h) => h.scenario_id === id && h.status === "COMPLETED").length ?? 0;
  return (
    <Shell>
      <PageTitle title="Simulations" lead="Choisissez une situation, puis parlez naturellement. Vous pouvez recommencer autant de fois que nécessaire." />
      <div className="relative max-w-md">
        <label htmlFor="search" className="sr-only">Rechercher une simulation</label>
        <Search size={18} aria-hidden className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate" />
        <input id="search" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher une simulation"
          className="h-12 w-full rounded-xl border border-[#CBD5E1] bg-white pl-11 pr-4 text-[15px]" />
      </div>
      {cats.length > 1 && <div role="group" aria-label="Catégories" className="flex flex-wrap gap-2">
        {["", ...cats].map((c) => <button key={c || "all"} type="button" aria-pressed={cat === c} onClick={() => setCat(c)}
          className={`min-h-11 rounded-full border px-4 text-sm font-medium ${cat === c ? "border-night bg-night text-white" : "border-[#CBD5E1] bg-white text-night hover:bg-[#F1F4F9]"}`}>{c || "Toutes"}</button>)}</div>}
      {sc.isLoading && <Spinner />}<ErrorBox error={sc.error} />
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{shown.map((s) => <ScenarioCard key={s.id} s={s} attempts={attempts(s.scenario_id)} />)}</div>
      {sc.data && shown.length === 0 && (
        <div className="rounded-2xl border border-dashed border-[#8896AB] bg-white p-10 text-center">
          <p className="font-semibold">Aucune simulation ne correspond à votre recherche</p><p className="mt-1 text-sm text-body">Essayez un autre mot-clé ou revenez à toutes les catégories.</p>
        </div>
      )}
    </Shell>
  );
}
