export interface LeadScheduleLine {
  line_id: string;
  account_code: string;
  account_name: string;
  balance: string;
  prior_year_balance: string | null;
  movement: string | null;
}

export interface LeadScheduleSummary {
  fs_area: string;
  line_count: number;
  balance: string;
  prior_year_balance: string | null;
  movement: string | null;
}

export interface LeadSchedule extends LeadScheduleSummary {
  lines: LeadScheduleLine[];
}

export interface PlanningSummary {
  engagement_id: string;
  engagement_status: string;
  trial_balance: {
    imported: boolean;
    line_count: number;
    unmapped_count: number;
  };
  materiality: {
    status: string;
    overall_materiality: string;
    performance_materiality: string;
    clearly_trivial_threshold: string;
  } | null;
  risks: {
    total: number;
    significant: number;
    entity_level: number;
    assertion_level: number;
    by_combined_rating: Record<string, number>;
  };
  procedures: {
    total: number;
    by_status: Record<string, number>;
    overdue: number;
    unassigned: number;
  };
}

export interface MyProcedure {
  id: string;
  engagement_id: string;
  engagement_status: string;
  fiscal_year: number;
  client_name: string | null;
  fs_area: string;
  title: string;
  isa_reference: string | null;
  status: string;
  due_date: string | null;
  overdue: boolean;
}
