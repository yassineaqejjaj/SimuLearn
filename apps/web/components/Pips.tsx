/** Jauge à 5 pastilles. Un score absent est affiché en pointillés, jamais comme 0. */
export function Pips({ score, label }: { score: number | null; label: string }) {
  return (
    <div className="flex gap-1" role="img" aria-label={score === null ? `${label} : non évalué` : `${label} : ${score} sur 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={`h-2 w-[22px] rounded ${score === null ? "border border-dashed border-[#AAB5C6]" : n <= score ? "bg-action" : "bg-[#DCE3EE]"}`} />
      ))}
    </div>
  );
}
