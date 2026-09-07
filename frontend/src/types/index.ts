export type CollectorParty = "BAYI" | "FRANCHISOR";

export type TurnoverSource = "kendi_islemleri" | "kendi_departmani" | "tum_bayi";

export type UserRole = "FRANCHISOR_ADMIN" | "BAYI_ADMIN" | "VIEWER";

export interface User {
  id: number;
  username: string;
  full_name?: string;
  role: UserRole;
  franchisor_id?: number | null;
  branch_id?: number | null;
  is_active: boolean;
  created_at?: string;
}

export interface Branch {
  id: number;
  franchisor_id?: number | null;
  name: string;
  tax_id?: string | null;
  tax_office?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Department {
  id: number;
  branch_id: number;
  name: string;
  is_active: boolean;
  created_at?: string;
}

export interface CommissionTier {
  id?: number;
  branch_id?: number;
  min_amount: number | string;
  max_amount: number | string | null;
  rate: number | string;
  created_at?: string;
}

export interface RoleCommissionTier {
  id?: number;
  role_id?: number;
  min_amount: number | string;
  max_amount: number | string | null;
  rate: number | string;
  created_at?: string;
}

export interface Role {
  id: number;
  branch_id: number;
  name: string;
  turnover_source: TurnoverSource;
  is_active: boolean;
  commission_tiers: RoleCommissionTier[];
  created_at?: string;
}

export interface TransactionCategory {
  id: number;
  branch_id: number;
  name: string;
  general_override_rate?: number | string | null;
  bonus_override_rate?: number | string | null;
  is_active: boolean;
  created_at?: string;
}

export interface Employee {
  id: number;
  branch_id: number;
  role_id: number;
  department_id?: number | null;
  full_name: string;
  is_active: boolean;
  role_name?: string;
  department_name?: string;
  role?: Role;
  created_at?: string;
}

export interface Transaction {
  id?: number;
  branch_id?: number;
  department_id: number;
  department_name?: string;
  employee_id?: number | null;
  employee_name?: string | null;
  category_id?: number | null;
  category_name?: string | null;
  date: string;
  customer_name: string;
  customer_tax_id?: string | null;
  customer_tax_id_masked?: string | null;
  item_name: string;
  staff_name?: string | null;
  amount_excl_vat: number | string;
  vat_rate: number | string;
  amount_incl_vat: number | string;
  payment_method?: string | null;
  invoice_status?: string | null;
  description?: string | null;
  created_at?: string;
}

export interface DepartmentSummary {
  department_id: number;
  department_name: string;
  transaction_count: number;
  total_turnover_excl_vat: string;
  percentage_of_total: string;
}

export interface InvoiceSummary {
  collector_party: CollectorParty;
  issuer: string;
  recipient: string;
  description: string;
  amount_excl_vat: string;
  vat_rate: string;
  vat_amount: string;
  total_amount_incl_vat: string;
}

export interface ReconciliationReport {
  year: number;
  month: number;
  branch_name: string;
  total_transactions: number;
  total_turnover_excl_vat: string;
  override_transactions_count?: number;
  override_turnover_excl_vat?: string;
  override_bayi_share_excl_vat?: string;
  standard_turnover_excl_vat?: string;
  standard_bayi_share_excl_vat?: string;
  applied_tier: CommissionTier | null;
  applied_rate_percentage: string;
  rate_explanation: string;
  bayi_share_rate: string;
  bayi_share_excl_vat: string;
  franchisor_share_rate: string;
  franchisor_share_excl_vat: string;
  invoice_summary: InvoiceSummary;
  department_breakdown: DepartmentSummary[];
  is_setting_persisted?: boolean;
  is_locked?: boolean;
  is_closed?: boolean;
  closed_at?: string;
  closed_by_name?: string;
}

export interface EmployeeBonusItem {
  employee_id: number;
  employee_name: string;
  role_id: number;
  role_name: string;
  department_id?: number | null;
  department_name?: string | null;
  turnover_source: TurnoverSource;
  transaction_count: number;
  standard_turnover_excl_vat: string;
  standard_tier_rate: string;
  standard_bonus: string;
  override_turnover_excl_vat: string;
  override_bonus: string;
  total_turnover_excl_vat: string;
  total_bonus: string;
  effective_bonus_rate: string;
  tier_explanation: string;
}

export interface PeriodBonusReport {
  period: string;
  total_employees: number;
  total_transactions: number;
  total_turnover_excl_vat: string;
  grand_total_bonus: string;
  items: EmployeeBonusItem[];
  is_closed?: boolean;
  closed_at?: string;
  closed_by_name?: string;
}

export interface UploadPreviewResponse {
  file_id: string;
  file_name: string;
  file_headers: string[];
  suggested_mapping: Record<string, string | null>;
  preview_rows: Record<string, any>[];
  total_rows: number;
}

export interface ImportRowError {
  row_index: number;
  raw_data: Record<string, any>;
  error_message: string;
}

export interface ImportResultResponse {
  total_rows: number;
  successful_count: number;
  failed_count: number;
  errors: ImportRowError[];
}

// Dashboard Types
export interface BranchTurnoverSummary {
  branch_id: number;
  branch_name: string;
  total_turnover: string | number;
  franchisor_share: string | number;
  bayi_share: string | number;
  transaction_count: number;
  collector_party: string;
  invoice_direction: string;
  invoice_net_payable: string | number;
}

export interface FranchisorDashboardTotals {
  total_branches: number;
  active_branches: number;
  total_turnover: string | number;
  total_franchisor_share: string | number;
  total_bayi_share: string | number;
  total_transactions: number;
}

export interface FranchisorDashboardData {
  year: number;
  month: number;
  totals: FranchisorDashboardTotals;
  branches: BranchTurnoverSummary[];
}

export interface MonthlyTrendItem {
  period: string;
  year: number;
  month: number;
  turnover: string | number;
  franchisor_share: string | number;
  bayi_share: string | number;
  transaction_count: number;
}

export interface DepartmentBreakdownItem {
  department_id: number;
  department_name: string;
  turnover: string | number;
  transaction_count: number;
  percentage: string | number;
}

export interface TopEmployeeBonusItem {
  rank: number;
  employee_id: number;
  employee_name: string;
  role_name: string;
  department_name?: string | null;
  turnover: string | number;
  bonus_amount: string | number;
}

export interface BranchDashboardSummary {
  branch_id: number;
  branch_name: string;
  year: number;
  month: number;
  total_turnover: string | number;
  franchisor_share: string | number;
  bayi_share: string | number;
  total_bonuses: string | number;
  net_bayi_margin: string | number;
  transaction_count: number;
  collector_party: string;
}

export interface BranchDashboardData {
  summary: BranchDashboardSummary;
  monthly_trends: MonthlyTrendItem[];
  department_breakdown: DepartmentBreakdownItem[];
  top_bonus_employees: TopEmployeeBonusItem[];
}

// Phase 4 Types: Rule Versioning & Period Closure
export interface PeriodClosureStatus {
  year: number;
  month: number;
  is_closed: boolean;
  status: "OPEN" | "CLOSURE_REQUESTED" | "CLOSED" | "REOPENED" | null;
  closure_id?: number | null;
  closed_at?: string | null;
  closed_by_name?: string | null;
  reopen_reason?: string | null;
}

export interface PeriodClosure {
  id: number;
  branch_id: number;
  year: number;
  month: number;
  status: string;
  closed_at: string;
  closed_by_user_id?: number | null;
  reconciliation_snapshot?: any;
  bonus_snapshot?: any;
  reopened_at?: string | null;
  reopened_by_user_id?: number | null;
  reopen_reason?: string | null;
  created_at: string;
}

export interface RuleChangeLog {
  id: number;
  branch_id: number;
  user_id?: number | null;
  rule_type: string;
  entity_id?: number | null;
  action: string;
  effective_from: string;
  description?: string | null;
  old_values?: any;
  new_values?: any;
  created_at: string;
}

export interface SystemNotification {
  id: number;
  branch_id?: number | null;
  user_id?: number | null;
  type: string;
  title: string;
  message: string;
  payload?: any;
  channel: string;
  is_read: boolean;
  created_at: string;
  sent_at?: string | null;
}

export interface InvoiceDataExport {
  document_id: string;
  issue_date: string;
  period: string;
  currency: string;
  invoice_direction: string;
  collector_party: string;
  issuer: Record<string, any>;
  recipient: Record<string, any>;
  amount_excl_vat: string;
  vat_rate: string;
  vat_amount: string;
  total_amount_incl_vat: string;
  line_items: Array<{
    item_name: string;
    quantity: number;
    unit: string;
    unit_price: string;
    amount_excl_vat: string;
    vat_rate: string;
    vat_amount: string;
    amount_incl_vat: string;
  }>;
  closure_audit: {
    closure_id: number;
    closed_at: string;
    closed_by: string;
    status: string;
  };
}
