// ─── Auth ──────────────────────────────────────────────────────────────────
export type UserRole =
  | "ceo"
  | "admin"
  | "sales"
  | "marketing"
  | "finance"
  | "operations"
  | "procurement";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  company_id: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  prefs?: Record<string, unknown> | null;
  onboarding_step?: number;
}

export interface Company {
  id: string;
  name: string;
  plan: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: "bearer";
}

// ─── API generic ─────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// ─── Upload ───────────────────────────────────────────────────────────────────
export type Department = "sales" | "marketing" | "operations" | "finance" | "procurement";
export type UploadStatus = "queued" | "processing" | "complete" | "rejected" | "error";

export interface Upload {
  id: string;
  dept: Department;
  original_name: string;
  status: UploadStatus;
  rows_total: number | null;
  rows_clean: number | null;
  rows_rejected: number | null;
  created_at: string;
}

// ─── Alert Preferences ────────────────────────────────────────────────────────
export interface AlertPrefs {
  email_alerts_enabled: boolean;
  alert_on_anomalies: boolean;
  alert_on_low_stock: boolean;
}

export interface AlertCheckResult {
  anomalies_found: number;
  low_stock_skus_found: number;
  emails_sent: number;
  notifications_created: number;
}

// ─── Notifications ────────────────────────────────────────────────────────────
export type NotificationSeverity = "info" | "warning" | "critical";

export interface Notification {
  id: string;
  type: NotificationSeverity;
  payload: { title?: string; message?: string; [key: string]: unknown };
  read_at: string | null;
  created_at: string;
}

// ─── Sales Analytics ─────────────────────────────────────────────────────────
export interface SkuRevenue {
  sku: string;
  revenue: number;
}

export interface RegionRevenue {
  region: string;
  revenue: number;
}

export interface DailyRevenue {
  date: string;
  revenue: number;
}

export interface SalesKpisOut {
  total_revenue: number;
  total_units: number;
  aov: number;
  top_sku: string | null;
  top_skus: SkuRevenue[];
  revenue_by_region: RegionRevenue[];
  daily_revenue: DailyRevenue[];
  deltas?: Record<string, number>;
}

// ─── Marketing Analytics ─────────────────────────────────────────────────────
export interface CampaignKpis {
  campaign_id: string;
  conversions: number;
}

export interface CampaignSpend {
  campaign_id: string;
  spend: number;
}

export interface DailySpend {
  date: string;
  spend: number;
}

export interface MarketingKpisOut {
  total_spend: number;
  total_conversions: number;
  total_impressions: number;
  ctr: number;
  roas: number;
  cac: number;
  top_campaigns: CampaignKpis[];
  spend_by_campaign: CampaignSpend[];
  daily_spend: DailySpend[];
  deltas?: Record<string, number>;
}

// ─── Operations Analytics ─────────────────────────────────────────────────────
export interface WarehouseStock {
  warehouse: string;
  stock_level: number;
}

export interface LowStockSku {
  sku: string;
  stock_level: number;
  reorder_point: number;
}

export interface DailyStockLevel {
  date: string;
  avg_stock_level: number;
}

export interface OperationsKpisOut {
  total_skus: number;
  total_stock_units: number;
  skus_below_reorder: number;
  active_warehouses: number;
  stock_by_warehouse: WarehouseStock[];
  low_stock_skus: LowStockSku[];
  daily_stock_level: DailyStockLevel[];
  deltas?: Record<string, number>;
}

// ─── Finance Analytics ────────────────────────────────────────────────────────
export interface CategoryRevenue {
  category: string;
  revenue: number;
}

export interface DailyGrossProfit {
  date: string;
  gross_profit: number;
}

export interface MonthlyPnL {
  month: string;
  revenue: number;
  cogs: number;
}

export interface FinanceKpisOut {
  total_revenue: number;
  total_cogs: number;
  total_gross_profit: number;
  gross_margin: number;
  revenue_by_category: CategoryRevenue[];
  daily_gross_profit: DailyGrossProfit[];
  monthly_pnl: MonthlyPnL[];
  deltas?: Record<string, number>;
}

// ─── AI Insights ─────────────────────────────────────────────────────────────
export interface InsightItem {
  dept: string;
  text: string;
}

export interface AnomalyPoint {
  date: string;
  revenue: number;
  z_score: number;
}

export interface InsightsOut {
  summary: string;
  insights: InsightItem[];
  generated_by: string;
}

// ─── Dashboard Summary ────────────────────────────────────────────────────────
export interface DashboardSummaryOut {
  total_revenue: number;
  top_sku: string | null;
  roas: number;
  marketing_spend: number;
  skus_below_reorder: number;
  active_warehouses: number;
  gross_margin: number;
  total_gross_profit: number;
  procurement_spend: number;
  unique_suppliers: number;
  avg_lead_days: number;
  daily_revenue: DailyRevenue[];
}

// ─── Procurement Analytics ────────────────────────────────────────────────────
export interface SupplierSpend {
  supplier_id: string;
  spend: number;
}

export interface SkuCost {
  sku: string;
  avg_unit_cost: number;
}

export interface ProcurementKpisOut {
  total_spend: number;
  total_units: number;
  unique_suppliers: number;
  avg_lead_days: number;
  top_suppliers: SupplierSpend[];
  daily_spend: DailySpend[];
  top_sku_costs: SkuCost[];
  deltas?: Record<string, number>;
}

// ─── Forecasting ─────────────────────────────────────────────────────────────
export interface ForecastPoint {
  ds: string;
  yhat: number;
  yhat_lower: number;
  yhat_upper: number;
}

export interface SkuForecast {
  sku: string;
  points: ForecastPoint[];
}

export interface ForecastOut {
  forecasts: SkuForecast[];
}

// ─── Chat ────────────────────────────────────────────────────────────────────
export interface ChatResponse {
  answer: string;
  tool_used: string | null;
  data: Record<string, unknown> | null;
  provider: string;
}

// ─── Health ───────────────────────────────────────────────────────────────────
export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  environment: string;
  services: Record<string, { status: string; detail: string }>;
}

// ─── Observability ────────────────────────────────────────────────────────────
export interface EndpointStat {
  endpoint: string;
  method: string;
  request_count: number;
  avg_duration_ms: number;
  error_rate: number;
}

export interface HourlyBucket {
  hour: string;
  requests: number;
  errors: number;
}

export interface ObservabilityDashboardOut {
  total_requests_24h: number;
  error_count_24h: number;
  error_rate_24h: number;
  avg_duration_ms_24h: number;
  p95_duration_ms_24h: number;
  hourly_volume: HourlyBucket[];
  top_endpoints: EndpointStat[];
}

export interface CeleryTaskStat {
  task_name: string;
  total: number;
  success: number;
  failure: number;
  success_rate: number;
  avg_duration_ms: number;
}

export interface RecentFailure {
  task_name: string;
  error: string | null;
  timestamp: string;
}

export interface CeleryStatsOut {
  total_tasks_24h: number;
  success_count_24h: number;
  failure_count_24h: number;
  success_rate_24h: number;
  avg_duration_ms_24h: number;
  by_task: CeleryTaskStat[];
  recent_failures: RecentFailure[];
}

// ─── AI Usage ────────────────────────────────────────────────────────────────
export interface AiUsageSummaryOut {
  total_calls_24h: number;
  total_tokens_in_24h: number;
  total_tokens_out_24h: number;
  total_tokens_24h: number;
  total_cost_usd_24h: number;
  cache_hit_rate_24h: number;
  avg_latency_ms_24h: number;
  calls_by_provider: Record<string, number>;
}

// ─── Cache ────────────────────────────────────────────────────────────────────
export interface CacheMetrics {
  hits: number;
  misses: number;
  stale_hits: number;
  hit_rate: number;
  total_lookups: number;
}

export interface CacheHealth {
  status: "healthy" | "unhealthy" | "unknown";
  latency_ms: number;
  used_memory_human?: string;
  connected_clients?: number;
  error?: string;
}

export interface CacheStatsOut {
  total_keys: number;
  by_category: Record<string, number>;
  metrics: CacheMetrics;
  health: CacheHealth;
}

export interface CacheInvalidateResult {
  deleted: number;
  dept: string | null;
  warmed: Record<string, boolean> | null;
}

export interface CacheWarmResult {
  company_id: string;
  warmed: Record<string, boolean>;
}

// ─── Task System ─────────────────────────────────────────────────────────────
export type TaskStatus =
  | "open"
  | "in_progress"
  | "blocked"
  | "in_review"
  | "done"
  | "cancelled";

export type TaskPriority = "low" | "medium" | "high" | "urgent" | "critical";
export type TaskType =
  | "general"
  | "anomaly_response"
  | "reorder"
  | "approval"
  | "review"
  | "incident";
export type TaskSource =
  | "manual"
  | "ai_recommendation"
  | "alert"
  | "anomaly"
  | "forecast"
  | "schedule";
export type AssigneeRole = "owner" | "collaborator" | "reviewer" | "watcher";
export type ActivityKind =
  | "created"
  | "status_changed"
  | "assigned"
  | "commented"
  | "kpi_updated"
  | "ai_suggested";

export interface TaskAssigneeOut {
  user_id: string;
  role_in_task: AssigneeRole;
  assigned_at: string;
}

export interface TaskOut {
  id: string;
  company_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  task_type: TaskType;
  source: TaskSource;
  departments: string[];
  assignees: TaskAssigneeOut[];
  due_at: string | null;
  sla_hours: number | null;
  breached: boolean;
  task_metadata: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TaskActivityOut {
  id: string;
  task_id: string;
  user_id: string | null;
  kind: ActivityKind;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface TaskCommentOut {
  id: string;
  task_id: string;
  user_id: string;
  body: string;
  created_at: string;
  edited_at: string | null;
}

export interface TaskDetailOut extends TaskOut {
  activity: TaskActivityOut[];
  comments: TaskCommentOut[];
}

export interface TaskListResponse {
  items: TaskOut[];
  total: number;
  page: number;
  size: number;
}

export interface ActivityListResponse {
  items: TaskActivityOut[];
  total: number;
  page: number;
  size: number;
}

// ─── Task Analytics ──────────────────────────────────────────────────────────

export interface DepartmentProductivity {
  department: string;
  total: number;
  done: number;
  in_progress: number;
  blocked: number;
  completion_rate: number;
}

export interface UserWorkload {
  user_id: string;
  open_count: number;
  in_progress_count: number;
  blocked_count: number;
  overdue_count: number;
  total_open: number;
}

export interface BottleneckTask {
  task_id: string;
  title: string;
  status: string;
  priority: string;
  days_stuck: number;
  departments: string[];
  breached: boolean;
}

export interface TeamScore {
  total_tasks: number;
  done_tasks: number;
  open_tasks: number;
  overdue_tasks: number;
  completion_rate: number;
  on_time_rate: number;
  avg_cycle_days: number;
}

export interface TaskAnalyticsDashboard {
  department_productivity: DepartmentProductivity[];
  workload: UserWorkload[];
  bottlenecks: BottleneckTask[];
  team_score: TeamScore;
}

export interface TaskRecommendationOut {
  id: string;
  title: string;
  description: string | null;
  priority: string;
  departments: string[];
  source: string;
  task_metadata: Record<string, unknown>;
  created_at: string;
}

export interface TaskRecommendationListResponse {
  items: TaskRecommendationOut[];
  total: number;
  page: number;
  size: number;
}

// ─── Sprints & Milestones ─────────────────────────────────────────────────────

export type SprintStatus = "planning" | "active" | "completed" | "cancelled";
export type MilestoneStatus = "active" | "completed" | "cancelled";

export interface MilestoneOut {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  due_at: string | null;
  status: MilestoneStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MilestoneListResponse {
  items: MilestoneOut[];
  total: number;
  page: number;
  size: number;
}

export interface SprintOut {
  id: string;
  company_id: string;
  name: string;
  goal: string | null;
  starts_at: string;
  ends_at: string;
  status: SprintStatus;
  capacity_hours: number | null;
  task_ids: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface SprintListResponse {
  items: SprintOut[];
  total: number;
  page: number;
  size: number;
}

// ─── Task Approvals ───────────────────────────────────────────────────────────

export type ApprovalDecisionValue = "approved" | "rejected";

export interface ApprovalOut {
  id: string;
  task_id: string;
  approver_id: string;
  requested_by: string;
  decision: ApprovalDecisionValue | null;
  note: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface ApprovalListResponse {
  items: ApprovalOut[];
  total: number;
  page: number;
  size: number;
}

// ─── Audit Log ────────────────────────────────────────────────────────────────
export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource: string;
  resource_id: string | null;
  ip: string | null;
  ua: string | null;
  created_at: string;
}

export interface AuditLogsResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  pageSize: number;
  sort?: string;
  filters?: Record<string, string>;
}

// ─── Inventory Intelligence ───────────────────────────────────────────────────
export interface InventoryOverviewOut {
  total_inventory_value: number;
  total_skus: number;
  total_stock_units: number;
  skus_at_risk: number;
  stockout_risk_skus: number;
  dead_stock_value: number;
  reorder_queue_count: number;
  avg_health_score: number;
}

export interface SkuSummaryOut {
  sku: string;
  current_stock: number;
  reorder_point: number;
  avg_unit_cost: number;
  total_value: number;
  days_on_hand: number | null;
  abc_class: string | null;
  xyz_class: string | null;
  avg_daily_demand: number;
}

export interface SkuListOut {
  items: SkuSummaryOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface AbcMatrixOut {
  segments: Record<string, string[]>;
  sku_counts: Record<string, number>;
  revenue_pcts: Record<string, number>;
  total_revenue: number;
}

export interface XyzMatrixOut {
  segments: Record<string, string[]>;
  sku_counts: Record<string, number>;
  cv_ranges: Record<string, string>;
}

export interface AbcXyzCell {
  abc: string;
  xyz: string;
  sku_count: number;
  total_revenue: number;
  skus: string[];
}

export interface AbcXyzMatrixOut {
  cells: AbcXyzCell[];
  total_skus: number;
  total_revenue: number;
}

export interface AgingBucket {
  bucket: string;
  sku_count: number;
  total_value: number;
  skus: string[];
}

export interface AgingOut {
  buckets: AgingBucket[];
  total_skus: number;
  total_value: number;
}

export interface CategoryValuation {
  category: string;
  cost_value: number;
  retail_value: number;
  sku_count: number;
}

export interface ValuationOut {
  total_cost_value: number;
  total_retail_value: number;
  potential_margin: number;
  by_category: CategoryValuation[];
}

export interface SkuVelocity {
  sku: string;
  units_sold: number;
  current_stock: number;
  sell_through: number;
  avg_unit_cost: number;
  revenue: number;
}

export interface VelocityOut {
  fast_movers: SkuVelocity[];
  slow_movers: SkuVelocity[];
  avg_sell_through: number;
  total_skus_analyzed: number;
}

// ─── Inventory Intelligence (Session 33) ──────────────────────────────────────

export interface ReorderItem {
  id: string;
  sku: string;
  current_stock: number;
  reorder_point: number;
  safety_stock: number;
  eoq: number;
  avg_daily_demand: number;
  lead_time_days: number;
  days_until_stockout: number | null;
  priority: "critical" | "high" | "medium";
  recommended_order_qty: number;
  estimated_cost: number;
}

export interface ReorderQueueOut {
  items: ReorderItem[];
  total: number;
}

export interface ReorderAcceptOut {
  message: string;
  po_id: string | null;
  sku: string;
  quantity: number;
}

export interface SkuHealthScore {
  sku: string;
  score: number;
  components: Record<string, number>;
  category: string | null;
  abc_class: string | null;
  xyz_class: string | null;
}

export interface HealthScoreOut {
  avg_score: number;
  top_skus: SkuHealthScore[];
  bottom_skus: SkuHealthScore[];
  distribution: Record<string, number>;
  total_skus: number;
}

export interface InventoryAnomalyItem {
  sku: string;
  anomaly_type: "demand_spike" | "demand_drop" | "unusual_pattern";
  severity: "high" | "medium" | "low";
  metric_value: number;
  baseline_value: number;
  detected_at: string;
}

export interface AnomalyOut {
  anomalies: InventoryAnomalyItem[];
  total: number;
}

export interface SeasonalityPoint {
  date: string;
  value: number;
}

export interface SeasonalityOut {
  sku: string;
  trend: SeasonalityPoint[];
  seasonal: SeasonalityPoint[];
  residual: SeasonalityPoint[];
  period_days: number;
  has_yearly_pattern: boolean;
}

export interface ExplanationOut {
  recommendation_id: string;
  rationale: string;
  confidence: "high" | "medium" | "low";
  key_factors: string[];
  alternatives: string[];
  cached: boolean;
}

export interface CopilotAskIn {
  question: string;
  context?: Record<string, unknown>;
}

export interface CopilotAskOut {
  answer: string;
  context_used: string[];
  provider: string;
}

export interface PoLineItem {
  sku: string;
  quantity: number;
  unit_cost: number;
  line_total: number;
}

export interface SupplierPoDraft {
  supplier_name: string;
  lines: PoLineItem[];
  total_cost: number;
  lead_time_days: number;
  expected_delivery: string;
  sku_count: number;
  priority: string;
}

export interface ReplenishmentOut {
  po_drafts: SupplierPoDraft[];
  total_suggested_cost: number;
}

export interface DeadStockItem {
  sku: string;
  current_stock: number;
  last_sold_days_ago: number;
  tied_up_value: number;
  doh: number | null;
}

export interface DeadStockOut {
  items: DeadStockItem[];
  total_tied_up_value: number;
  total: number;
}

export interface OverstockItem {
  sku: string;
  current_stock: number;
  doh: number;
  excess_units: number;
  excess_value: number;
  target_doh: number;
}

export interface OverstockOut {
  items: OverstockItem[];
  total_excess_value: number;
  total: number;
}

export interface UnderstockItem {
  sku: string;
  current_stock: number;
  reorder_point: number;
  days_until_stockout: number | null;
  shortage_units: number;
  priority: string;
}

export interface UnderstockOut {
  items: UnderstockItem[];
  total: number;
}

export interface HeatmapCell {
  warehouse: string;
  category: string;
  health_score: number;
  sku_count: number;
  total_value: number;
}

export interface HeatmapOut {
  cells: HeatmapCell[];
  warehouses: string[];
  categories: string[];
}
