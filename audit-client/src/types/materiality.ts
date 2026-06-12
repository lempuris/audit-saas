export type MaterialityBenchmark =
  | "revenue"
  | "total_assets"
  | "profit_before_tax"
  | "equity"
  | "total_expenses"
  | "custom";

export const MATERIALITY_BENCHMARKS: MaterialityBenchmark[] = [
  "revenue",
  "total_assets",
  "profit_before_tax",
  "equity",
  "total_expenses",
  "custom",
];

export interface MaterialityInput {
  benchmark: MaterialityBenchmark;
  benchmark_amount: string;
  overall_percentage: string;
  performance_percentage: string;
  clearly_trivial_percentage: string;
  rationale: string | null;
}

export interface MaterialityRecord extends MaterialityInput {
  id: string;
  engagement_id: string;
  overall_materiality: string;
  performance_materiality: string;
  clearly_trivial_threshold: string;
  status: "draft" | "approved";
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}
