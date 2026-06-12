export type FSArea =
  | "property_plant_equipment"
  | "intangible_assets"
  | "investments"
  | "inventory"
  | "trade_receivables"
  | "cash_and_bank"
  | "other_assets"
  | "trade_payables"
  | "borrowings"
  | "provisions"
  | "other_liabilities"
  | "equity"
  | "revenue"
  | "cost_of_sales"
  | "operating_expenses"
  | "other_income"
  | "finance_costs"
  | "tax";

export const FS_AREAS: FSArea[] = [
  "property_plant_equipment",
  "intangible_assets",
  "investments",
  "inventory",
  "trade_receivables",
  "cash_and_bank",
  "other_assets",
  "trade_payables",
  "borrowings",
  "provisions",
  "other_liabilities",
  "equity",
  "revenue",
  "cost_of_sales",
  "operating_expenses",
  "other_income",
  "finance_costs",
  "tax",
];

export function fsAreaLabel(area: string | null): string {
  if (!area) return "Unmapped";
  return area.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
}

export interface ColumnMapping {
  account_code: string;
  account_name: string;
  balance?: string | null;
  debit?: string | null;
  credit?: string | null;
  prior_year_balance?: string | null;
}

export interface TrialBalancePreview {
  columns: string[];
  rows: Record<string, string | null>[];
  total_rows: number;
}

export interface TrialBalanceLineRecord {
  id: string;
  account_code: string;
  account_name: string;
  balance: string;
  prior_year_balance: string | null;
  fs_area: string | null;
}

export interface TrialBalanceDetail {
  id: string;
  engagement_id: string;
  source_filename: string;
  imported_by: string;
  created_at: string;
  updated_at: string;
  lines: TrialBalanceLineRecord[];
}

export interface FSAreaSummary {
  fs_area: string | null;
  line_count: number;
  balance: string;
  prior_year_balance: string | null;
  movement: string | null;
}
