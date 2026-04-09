export interface MinamataData {
  id: number;
  month: string;
  no_of_strings_breakdown: number | string;
  no_of_strings_modules_damaged?: string;
  designed_dc_capacity_mwh?: number | string;
  breakdown_dc_capacity_mwh?: number | string;
  operational_dc_capacity_mwh?: number | string;
  budgeted_gen_mwh: number | string;
  actual_gen_mwh?: number | string;
  loss_due_to_string_failure_mwh: number | string;
  loss_in_jpy?: number | string;
  loss_in_usd: number | string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown; // Allow for other properties
}

export interface MinamataTableRow {
  month: string;
  no_of_strings_breakdown: number | string;
  budgeted_gen_mwh: number;
  loss_due_to_string_failure_mwh: number;
  loss_in_usd: number;
  isTotal?: boolean;
}

