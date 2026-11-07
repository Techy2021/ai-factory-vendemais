type ScoreKind = "missing" | "high" | "medium" | "low";

export function scorePresentation(score: number | null): { kind: ScoreKind; label: string } {
  if (score === null) return { kind: "missing", label: "Sem pontuação" };
  if (score >= 80) return { kind: "high", label: "Alta" };
  if (score >= 50) return { kind: "medium", label: "Média" };
  return { kind: "low", label: "Baixa" };
}
