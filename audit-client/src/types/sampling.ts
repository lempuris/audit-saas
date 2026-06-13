export type SampleMethod = "random" | "systematic" | "monetary_unit";

export const SAMPLE_METHODS: { value: SampleMethod; label: string }[] = [
  { value: "monetary_unit", label: "Monetary-unit (MUS)" },
  { value: "random", label: "Random" },
  { value: "systematic", label: "Systematic" },
];

export const CONFIDENCE_LEVELS = [80, 90, 95] as const;

export interface SampleComputation {
  method: string;
  sample_size: number;
  reliability_factor: string;
  selection_basis: Record<string, unknown>;
}

export interface SampleRecord {
  id: string;
  engagement_id: string;
  working_paper_id: string | null;
  fs_area: string | null;
  population_description: string;
  method: SampleMethod;
  population_size: number | null;
  population_value: string;
  tolerable_misstatement: string;
  expected_misstatement: string;
  confidence_level: number;
  reliability_factor: string;
  sample_size: number;
  selection_basis: Record<string, unknown>;
  created_by: string;
  created_at: string;
}
