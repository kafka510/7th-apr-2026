export type ScheduleType = 'interval' | 'crontab' | 'unknown';

export interface CrontabSpec {
  minute: string;
  hour: string;
  day_of_week: string;
  day_of_month: string;
  month_of_year: string;
}

export interface BackgroundJob {
  id: number;
  name: string;
  task: string;
  enabled: boolean;
  queue: string | null;
  schedule_type: ScheduleType;
  interval_seconds: number | null;
  crontab: CrontabSpec | null;
  args: string;   // JSON string
  kwargs: string; // JSON string
  description: string | null;
  last_run_at: string | null;
  total_run_count: number;
}

