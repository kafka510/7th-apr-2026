export type TicketDashboardMeta = {
  appliedFilters?: Record<string, unknown>;
  generatedAt: string;
};

export type BasicOption = {
  value: string;
  label: string;
  description?: string | null;
};

export type SubCategoryOption = BasicOption & {
  category: string;
};

export type SiteOption = BasicOption & {
  assetCode?: string | null;
  assetNumber?: string | null;
  country?: string | null;
  portfolio?: string | null;
};

export type TicketDashboardFilters = {
  statusOptions: BasicOption[];
  priorityOptions: BasicOption[];
  categoryOptions: BasicOption[];
  lossCategoryOptions: BasicOption[];
  siteOptions: SiteOption[];
};

export type ChartDataset = {
  labels: string[];
  values: number[];
};

export type TicketDashboardCharts = {
  status: ChartDataset;
  priority: ChartDataset;
  category: ChartDataset;
};

export type TicketDashboardKpis = {
  total_tickets: number;
  open_tickets: number;
  unassigned_tickets: number;
  overdue_tickets: number;
};

export type RecentTicket = {
  id: string;
  ticket_number: string;
  title: string;
  status: string;
  status_display: string;
  priority: string;
  priority_display: string;
  site_name: string;
  created_at: string;
};

export type TicketDeviceSummary = {
  device_name: string;
  device_serial: string;
  count: number;
};

export type LossByCategory = {
  category_name: string;
  total_loss: number;
  count: number;
};

export type LossByDevice = {
  device_name: string;
  device_make: string;
  device_model: string;
  total_loss: number;
  count: number;
};

export type AvgTimeToClose = {
  days: number;
  hours: number;
  minutes: number;
  total_seconds: number;
};

export type TicketDashboardSummary = {
  meta: TicketDashboardMeta;
  filters: TicketDashboardFilters;
  kpis: TicketDashboardKpis;
  charts: TicketDashboardCharts;
  recentTickets: RecentTicket[];
  ticketsByDevice: TicketDeviceSummary[];
  ticketsByStatus: Record<string, number>;
  avgTimeToClose?: AvgTimeToClose | null;
  losses: {
    total: number;
    byCategory: LossByCategory[];
    byDevice: LossByDevice[];
  };
};

export type TicketDashboardFilterParams = {
  status?: string;
  priority?: string;
  category?: string | number;
  site?: string | number;
  dateFrom?: string;
  dateTo?: string;
  [key: string]: unknown;
};

export type AnalyticsItem = {
  label: string;
  subLabel?: string | null;
  value: number;
  secondary: number;
  trend: number[];
  entityType: string;
  entityKey: unknown;
};

export type AnalyticsPagination = {
  page: number;
  perPage: number;
  totalItems: number;
  totalPages: number;
};

export type TicketAnalyticsResponse = {
  labels: string[];
  values: number[];
  items: AnalyticsItem[];
  pagination: AnalyticsPagination;
};

export type RecentTicketsResponse = {
  count: number;
  results: RecentTicket[];
};

export type TicketAnalyticsParams = TicketDashboardFilterParams & {
  viewBy?: string;
  page?: number;
  perPage?: number;
  trendDays?: number;
};

export type RecentTicketsParams = TicketDashboardFilterParams & {
  limit?: number;
  filterBy?: string;
  filterValue?: string;
};

export type TicketFilterState = {
  status?: string | string[];
  priority?: string | string[];
  category?: string | string[];
  site?: string | string[];
  dateFrom?: string;
  dateTo?: string;
  [key: string]: unknown;
};

export type TicketListItem = {
  id: string;
  ticket_number: string;
  title: string;
  status: string;
  status_display: string;
  priority: string;
  priority_display: string;
  category: string | null;
  sub_category?: string | null;
  asset_code: string | null;
  asset_name: string | null;
  asset_number: string | null;
  assigned_to_id: number | null;
  assigned_to: string | null;
  created_at: string;
  updated_at: string | null;
};

export type TicketListFilters = {
  statusOptions: BasicOption[];
  priorityOptions: BasicOption[];
  categoryOptions: BasicOption[];
  subCategoryOptions: SubCategoryOption[];
  siteOptions: SiteOption[];
  assigneeOptions: BasicOption[];
  assetNumberOptions: BasicOption[];
};

export type TicketListStatusBucket = {
  status: string;
  label: string;
  count: number;
};

export type TicketListSummary = {
  generatedAt: string;
  total: number;
  open: number;
  awaitingApproval: number;
  unassigned: number;
  critical: number;
  statusBreakdown: TicketListStatusBucket[];
};

export type TicketListResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: TicketListItem[];
  filterOptions?: TicketListFilters;
  summary?: TicketListSummary;
  permissions?: {
    canDelete: boolean;
  };
};

export type TicketListQueryState = {
  statuses: string[];
  priorities: string[];
  categories: string[];
  sites: string[];
  assignees: string[];
  assetNumbers: string[];
  dateFrom?: string;
  dateTo?: string;
  search?: string;
  sort?: string;
  order?: 'asc' | 'desc';
  page: number;
  pageSize: number;
  [key: string]: unknown;
};

export type TicketUser = {
  id: number;
  username: string;
  name: string;
} | null;

export type TicketSubCategoryInfo = {
  id: number;
  name: string;
  category_id: number;
} | null;

export type TicketMaterialEntry = {
  id: string;
  material_name: string;
  quantity: string;
  unit_price: string;
  created_at: string;
  updated_at: string;
};

export type TicketManpowerEntry = {
  id: string;
  person_name: string;
  hours_worked: string;
  hourly_rate: string;
  created_at: string;
  updated_at: string;
};

export type TicketDetail = {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  status: string;
  status_display: string;
  priority: string;
  priority_display: string;
  category: string | null;
  sub_category: TicketSubCategoryInfo;
  loss_category: string | null;
  asset_code: string | null;
  asset_name: string | null;
  assigned_to: TicketUser;
  created_by: TicketUser;
  updated_by: TicketUser;
  watchers: TicketUser[];
  created_at: string;
  updated_at: string | null;
  closed_at: string | null;
  metadata: Record<string, unknown>;
  materials: TicketMaterialEntry[];
  manpower: TicketManpowerEntry[];
  permissions: {
    canEdit: boolean;
    canAssign: boolean;
    canManageWatchers: boolean;
    canComment: boolean;
    canRemoveAssignee: boolean;
    canRemoveWatchers: boolean;
    canDelete: boolean;
  };
};

export type TicketTimelineEntry = {
  id: number;
  user: TicketUser;
  action: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  notes: string;
  created_at: string;
};

export type TicketComment = {
  id: number;
  user: TicketUser;
  comment: string;
  created_at: string;
  is_internal: boolean;
};

export type TicketAttachment = {
  id: number;
  file_name: string;
  file_url: string;
  file_size?: number | null;
  file_type?: string | null;
  uploaded_by: TicketUser;
  created_at: string;
};

export type TicketFormOptions = {
  sites: BasicOption[];
  categories: BasicOption[];
  subCategories: SubCategoryOption[];
  lossCategories: BasicOption[];
  priorities: BasicOption[];
  users: BasicOption[];
};

export type DeviceOption = {
  value: string;
  label: string;
  device_type?: string | null;
  device_sub_group?: string | null;
  warranty_expire_date?: string | null;
};

// Admin types
export type TicketCategory = {
  id: number;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type TicketSubCategory = {
  id: number;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
  category: {
    id: number;
    name: string;
  } | null;
  created_at: string;
  updated_at: string;
};

export type TicketSubCategoryInput = {
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
  category: number;
};

export type LossCategory = {
  id: number;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PMRule = {
  id: number;
  name: string;
  description: string;
  rule_type: 'date_based' | 'frequency_based';
  rule_type_display: string;
  date_field_name: string;
  alert_days_before: number | null;
  start_date_field: string;
  frequency_field: string;
  category: {
    id: number;
    name: string;
  } | null;
  priority: string;
  priority_display: string;
  title_template: string;
  description_template: string;
  assign_to_role: string;
  send_email_notification: boolean;
  is_active: boolean;
  created_by: {
    id: number;
    username: string;
  } | null;
  created_at: string | null;
  updated_at: string | null;
};

export type PMRuleInput = {
  name: string;
  description: string;
  rule_type: 'date_based' | 'frequency_based';
  category: number;
  priority: string;
  title_template: string;
  description_template: string;
  send_email_notification: boolean;
  is_active: boolean;
  date_field_name?: string | null;
  alert_days_before?: number | null;
  start_date_field?: string | null;
  frequency_field?: string | null;
  assign_to_role?: string | null;
};

export type TicketFormData = {
  title: string;
  description: string;
  asset_code: string;
  location?: string;
  device_type?: string;
  device_id?: string;
  sub_device_id?: string;
  category: string;
  sub_category?: string;
  loss_category?: string;
  loss_value?: number;
  priority: string;
  assigned_to?: string;
  watchers?: string[];
};

export type TicketMaterialInput = {
  material_name: string;
  quantity: number;
  unit_price: number;
};

export type TicketManpowerInput = {
  person_name: string;
  hours_worked: number;
  hourly_rate: number;
};

