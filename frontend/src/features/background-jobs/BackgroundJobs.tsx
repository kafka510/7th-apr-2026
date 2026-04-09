import { useEffect, useMemo, useState } from 'react';
import type { BackgroundJob, CrontabSpec } from './types';
import {
  createBackgroundJob,
  deleteBackgroundJob,
  downloadAllSchedulesAndTasks,
  importSchedulesFile,
  getFusionSolarBackfillAssets,
  getLaplaceBackfillAssets,
  getSolargisDailyApiCalls,
  getSolargisSourceAssets,
  listBackgroundJobs,
  listAvailableCeleryTasks,
  runBackgroundJobNow,
  runFusionSolarBackfill,
  runFusionSolarOemDailyKpiRun,
  runTaskOnDemand,
  updateBackgroundJob,
  queueErhParseInvoicePdf,
  getErhTaskStatus,
} from './api';
import { fetchAdapterAccounts, getAllAssets } from '../site-onboarding/api';
import type { AdapterAccount } from '../site-onboarding/types';

/** Celery task: daily KPI computation (scheduled previous day or on-demand date range). */
const KPI_COMPUTE_TASK = 'main.tasks.compute_daily_kpis_previous_day';

/** ERH utility invoice PDF parse (same task as Energy Revenue Hub async parse). */
const ERH_PARSE_TASK = 'energy_revenue_hub.tasks.erh_parse_invoice_files_task';

/** Fusion Solar on-demand backfill (historical window + related acquisition). */
const FUSION_SOLAR_BACKFILL_TASK = 'data_collection.tasks.run_fusion_solar_backfill';

/** Fusion Solar OEM daily only: getDevKpiDay for devTypeId 1 inverters → kpis.oem_daily_product_kwh; no 5-min backfill. */
const FUSION_SOLAR_OEM_DAILY_TASK = 'data_collection.tasks.run_fusion_solar_oem_daily_kpi';

function isFusionSolarWizardTask(task: string): boolean {
  return task === FUSION_SOLAR_BACKFILL_TASK || task === FUSION_SOLAR_OEM_DAILY_TASK;
}

interface Props {
  isSuperuser: boolean;
}

function scheduleSummary(job: BackgroundJob): string {
  if (job.schedule_type === 'interval') {
    return job.interval_seconds ? `Every ${job.interval_seconds}s` : 'Interval';
  }
  if (job.schedule_type === 'crontab') {
    const c = job.crontab;
    if (!c) return 'Crontab';
    return `${c.minute} ${c.hour} (DOW ${c.day_of_week})`;
  }
  return 'Unknown';
}

function safeJsonPretty(text: string, fallback: string) {
  try {
    const v = JSON.parse(text);
    return JSON.stringify(v, null, 2);
  } catch {
    return fallback;
  }
}

export function BackgroundJobs({ isSuperuser }: Props) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [taskOptions, setTaskOptions] = useState<string[]>([]);
  const [uploadingImport, setUploadingImport] = useState(false);
  const [replaceExistingOnImport, setReplaceExistingOnImport] = useState(false);
  const [importSummary, setImportSummary] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<BackgroundJob | null>(null);
  const [saving, setSaving] = useState(false);

  const [runOnDemandModalOpen, setRunOnDemandModalOpen] = useState(false);
  const [runOnDemandTask, setRunOnDemandTask] = useState('');
  const [runOnDemandArgs, setRunOnDemandArgs] = useState('[]');
  const [runOnDemandKwargs, setRunOnDemandKwargs] = useState('{}');
  const [runOnDemandQueue, setRunOnDemandQueue] = useState('');
  const [replaceAllDayData30Min, setReplaceAllDayData30Min] = useState(false);
  const [durationDays30Min, setDurationDays30Min] = useState<string>('');
  const [hourlyDurationDays, setHourlyDurationDays] = useState<string>('');
  const [laplaceSpanDateFrom, setLaplaceSpanDateFrom] = useState('');
  const [laplaceSpanDateTo, setLaplaceSpanDateTo] = useState('');
  const [laplaceBackfillAssets, setLaplaceBackfillAssets] = useState<string[]>([]);
  const [laplaceBackfillSelected, setLaplaceBackfillSelected] = useState<string[]>([]);
  const [runOnDemandLoading, setRunOnDemandLoading] = useState(false);
  /** When true, queued tasks include a Celery header so the worker emails the user on completion. */
  const [notifyEmailOnTaskCompletion, setNotifyEmailOnTaskCompletion] = useState(false);
  const [solargisDailyApiCalls, setSolargisDailyApiCalls] = useState<number | null>(null);
  const [solargisDateFrom, setSolargisDateFrom] = useState('');
  const [solargisDateTo, setSolargisDateTo] = useState('');
  const [solargisSourceAssets, setSolargisSourceAssets] = useState<string[]>([]);
  const [solargisSelectedAssets, setSolargisSelectedAssets] = useState<string[]>([]);
  const [solargisSourceAssetsLoaded, setSolargisSourceAssetsLoaded] = useState(false);
  const [solargisAllConfiguredCount, setSolargisAllConfiguredCount] = useState<number | null>(null);

  // Fusion Solar backfill (run-on-demand modal)
  const [fsBackfillAssets, setFsBackfillAssets] = useState<string[]>([]);
  const [fsBackfillSelected, setFsBackfillSelected] = useState<string[]>([]);
  const [fsBackfillDateFrom, setFsBackfillDateFrom] = useState('');
  const [fsBackfillDateTo, setFsBackfillDateTo] = useState('');
  const [fsOemMonthFrom, setFsOemMonthFrom] = useState('');
  const [fsOemMonthTo, setFsOemMonthTo] = useState('');
  const [fsAdapterId, setFsAdapterId] = useState<string>('fusion_solar');
  const [fsAccounts, setFsAccounts] = useState<AdapterAccount[]>([]);
  const [fsAccountId, setFsAccountId] = useState<number | ''>('');

  const [kpiAssets, setKpiAssets] = useState<string[]>([]);
  const [kpiSelectedAssets, setKpiSelectedAssets] = useState<string[]>([]);
  const [kpiDateFrom, setKpiDateFrom] = useState('');
  const [kpiDateTo, setKpiDateTo] = useState('');
  const [kpiAssetsLoaded, setKpiAssetsLoaded] = useState(false);

  /** ERH parse-from-modal: upload PDFs and poll Celery (validates worker + parser). */
  const [erhParseFiles, setErhParseFiles] = useState<File[]>([]);
  const [erhParseSessionId, setErhParseSessionId] = useState('');
  const [erhParseOutcome, setErhParseOutcome] = useState<Record<string, unknown> | null>(null);
  const [erhParseError, setErhParseError] = useState<string | null>(null);

  // form state
  const [name, setName] = useState('');
  const [task, setTask] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [queue, setQueue] = useState('');
  const [scheduleType, setScheduleType] = useState<'interval' | 'crontab'>('interval');
  const [intervalSeconds, setIntervalSeconds] = useState(300);
  const [crontab, setCrontab] = useState<CrontabSpec>({
    minute: '0',
    hour: '0',
    day_of_week: '*',
    day_of_month: '*',
    month_of_year: '*',
  });
  const [args, setArgs] = useState('[]');
  const [kwargs, setKwargs] = useState('{}');
  const [description, setDescription] = useState('');

  const sortedJobs = useMemo(() => {
    const copy = [...jobs];
    copy.sort((a, b) => a.name.localeCompare(b.name));
    return copy;
  }, [jobs]);

  /** Surface Fusion Solar tasks at the top of the on-demand task list when present. */
  const runOnDemandTaskOptions = useMemo(() => {
    const tasks = [...taskOptions];
    for (const t of [FUSION_SOLAR_OEM_DAILY_TASK, FUSION_SOLAR_BACKFILL_TASK]) {
      const idx = tasks.indexOf(t);
      if (idx >= 0) tasks.splice(idx, 1);
    }
    tasks.unshift(FUSION_SOLAR_OEM_DAILY_TASK, FUSION_SOLAR_BACKFILL_TASK);
    return tasks;
  }, [taskOptions]);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listBackgroundJobs();
      setJobs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  const handleImportSchedulesFile = async (file: File) => {
    setUploadingImport(true);
    setError(null);
    setImportSummary(null);
    try {
      const res = await importSchedulesFile(file, replaceExistingOnImport);
      const skippedCount = res.skipped.length;
      const errorCount = res.errors.length;
      setImportSummary(
        `Import completed: created ${res.created}, updated ${res.updated}, skipped ${skippedCount}, errors ${errorCount}.`,
      );
      if (errorCount > 0) {
        const firstErrors = res.errors
          .slice(0, 5)
          .map((e) => `${e.item}: ${e.reason}`)
          .join(' | ');
        setError(`Import finished with ${errorCount} error(s). ${firstErrors}`);
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setUploadingImport(false);
    }
  };

  const loadTaskOptions = async () => {
    try {
      const tasks = await listAvailableCeleryTasks();
      setTaskOptions(tasks);
    } catch {
      // Non-blocking; user can still type manually.
      setTaskOptions([]);
    }
  };

  // Load jobs & task options once when page opens
  useEffect(() => {
    if (!isSuperuser) return;
    void refresh();
    void loadTaskOptions();
  }, [isSuperuser]);

  useEffect(() => {
    if (
      !isSuperuser ||
      !runOnDemandModalOpen ||
      !isFusionSolarWizardTask(runOnDemandTask)
    )
      return;
    fetchAdapterAccounts(fsAdapterId)
      .then((res) => {
        const filtered = (res.data || []).filter((a) => a.adapter_id === fsAdapterId);
        setFsAccounts(filtered);
        setFsAccountId('');
      })
      .catch(() => {
        setFsAccounts([]);
        setFsAccountId('');
      });
  }, [isSuperuser, runOnDemandModalOpen, runOnDemandTask, fsAdapterId]);

  useEffect(() => {
    if (
      !isSuperuser ||
      !runOnDemandModalOpen ||
      !isFusionSolarWizardTask(runOnDemandTask)
    )
      return;
    getFusionSolarBackfillAssets({
      adapter_id: fsAdapterId,
      adapter_account_id: typeof fsAccountId === 'number' ? fsAccountId : null,
    })
      .then((r) => {
        const codes = r.asset_codes || [];
        setFsBackfillAssets(codes);
        setFsBackfillSelected(codes);
      })
      .catch(() => {
        setFsBackfillAssets([]);
        setFsBackfillSelected([]);
      });
  }, [isSuperuser, runOnDemandModalOpen, runOnDemandTask, fsAdapterId, fsAccountId]);

  // Prevent background scroll when modal is open (and align with Bootstrap behavior)
  useEffect(() => {
    if (!modalOpen && !runOnDemandModalOpen) return;
    document.body.classList.add('modal-open');
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.classList.remove('modal-open');
      document.body.style.overflow = prevOverflow;
    };
  }, [modalOpen, runOnDemandModalOpen]);

  const openCreate = () => {
    setEditing(null);
    setName('');
    setTask('');
    setEnabled(true);
    setQueue('');
    setScheduleType('interval');
    setIntervalSeconds(300);
    setCrontab({ minute: '0', hour: '0', day_of_week: '*', day_of_month: '*', month_of_year: '*' });
    setArgs('[]');
    setKwargs('{}');
    setDescription('');
    setModalOpen(true);
    void loadTaskOptions();
  };

  const openEdit = (job: BackgroundJob) => {
    setEditing(job);
    setName(job.name);
    setTask(job.task);
    setEnabled(job.enabled);
    setQueue(job.queue || '');
    setScheduleType(job.schedule_type === 'crontab' ? 'crontab' : 'interval');
    setIntervalSeconds(job.interval_seconds || 300);
    setCrontab(
      job.crontab || { minute: '0', hour: '0', day_of_week: '*', day_of_month: '*', month_of_year: '*' }
    );
    setArgs(safeJsonPretty(job.args || '[]', job.args || '[]'));
    setKwargs(safeJsonPretty(job.kwargs || '{}', job.kwargs || '{}'));
    setDescription(job.description || '');
    setModalOpen(true);
    void loadTaskOptions();
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (editing) {
        await updateBackgroundJob({
          id: editing.id,
          name,
          task,
          enabled,
          queue: queue.trim() ? queue.trim() : null,
          schedule_type: scheduleType,
          interval_seconds: scheduleType === 'interval' ? intervalSeconds : undefined,
          crontab: scheduleType === 'crontab' ? crontab : undefined,
          args,
          kwargs,
          description: description.trim() ? description.trim() : null,
        });
      } else {
        await createBackgroundJob({
          name,
          task,
          enabled,
          queue: queue.trim() ? queue.trim() : null,
          schedule_type: scheduleType,
          interval_seconds: scheduleType === 'interval' ? intervalSeconds : undefined,
          crontab: scheduleType === 'crontab' ? crontab : undefined,
          args,
          kwargs,
          description: description.trim() ? description.trim() : null,
        });
      }
      closeModal();
      await refresh();
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async (job: BackgroundJob) => {
    setError(null);
    try {
      await updateBackgroundJob({ id: job.id, enabled: !job.enabled });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    }
  };

  const runNow = async (job: BackgroundJob) => {
    setError(null);
    // For some tasks we want to open the Run-on-demand wizard instead of firing immediately
    if (job.task === FUSION_SOLAR_BACKFILL_TASK || job.task === FUSION_SOLAR_OEM_DAILY_TASK) {
      openRunOnDemand(job.task);
      return;
    }
    if (job.task === KPI_COMPUTE_TASK) {
      openRunOnDemand(job.task);
      return;
    }
    if (job.task === ERH_PARSE_TASK) {
      openRunOnDemand(job.task);
      return;
    }
    try {
      await runBackgroundJobNow(job.id, {
        send_completion_email: notifyEmailOnTaskCompletion,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run now failed');
    }
  };

  const openRunOnDemand = (taskName: string) => {
    setRunOnDemandTask(taskName);
    setRunOnDemandArgs('[]');
    setRunOnDemandKwargs('{}');
    setRunOnDemandQueue('');
    setReplaceAllDayData30Min(false);
    setDurationDays30Min('');
    setHourlyDurationDays('');
    setLaplaceSpanDateFrom('');
    setLaplaceSpanDateTo('');
    setLaplaceBackfillAssets([]);
    setLaplaceBackfillSelected([]);
    setSolargisDailyApiCalls(null);
    setSolargisDateFrom('');
    setSolargisDateTo('');
    setSolargisSourceAssets([]);
    setSolargisSelectedAssets([]);
    setSolargisSourceAssetsLoaded(false);
    setSolargisAllConfiguredCount(null);
    setFsBackfillAssets([]);
    setFsBackfillSelected([]);
    setFsBackfillDateFrom('');
    setFsBackfillDateTo('');
    {
      const d = new Date();
      const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      setFsOemMonthFrom(ym);
      setFsOemMonthTo(ym);
    }
    setFsAdapterId('fusion_solar');
    setFsAccounts([]);
    setFsAccountId('');
    setKpiAssets([]);
    setKpiSelectedAssets([]);
    setKpiDateFrom('');
    setKpiDateTo('');
    setKpiAssetsLoaded(false);
    setErhParseFiles([]);
    setErhParseSessionId('');
    setErhParseOutcome(null);
    setErhParseError(null);
    setRunOnDemandModalOpen(true);
  };

  // Fetch Solargis daily API count and source assets when opening Run on demand for run_solargis_daily_ingest
  useEffect(() => {
    if (
      !runOnDemandModalOpen ||
      runOnDemandTask !== 'data_collection.tasks.run_solargis_daily_ingest'
    ) {
      return;
    }
    getSolargisDailyApiCalls()
      .then((res) => setSolargisDailyApiCalls(res.total_api_calls))
      .catch(() => setSolargisDailyApiCalls(null));
    getSolargisSourceAssets()
      .then((res) => {
        const codes = res.asset_codes || [];
        setSolargisSourceAssets(codes);
        setSolargisSelectedAssets([...codes]);
        setSolargisAllConfiguredCount(res.all_configured_count ?? null);
        setSolargisSourceAssetsLoaded(true);
      })
      .catch(() => {
        setSolargisSourceAssets([]);
        setSolargisSelectedAssets([]);
        setSolargisAllConfiguredCount(null);
        setSolargisSourceAssetsLoaded(true);
      });
  }, [runOnDemandModalOpen, runOnDemandTask]);

  useEffect(() => {
    if (!runOnDemandModalOpen || runOnDemandTask !== KPI_COMPUTE_TASK) return;
    getAllAssets()
      .then((assets) => {
        const codes = assets.map((a) => a.asset_code).filter(Boolean).sort() as string[];
        setKpiAssets(codes);
        setKpiSelectedAssets([...codes]);
        setKpiAssetsLoaded(true);
      })
      .catch(() => {
        setKpiAssets([]);
        setKpiSelectedAssets([]);
        setKpiAssetsLoaded(true);
      });
  }, [runOnDemandModalOpen, runOnDemandTask]);

  useEffect(() => {
    if (
      !isSuperuser ||
      !runOnDemandModalOpen ||
      runOnDemandTask !== 'data_collection.tasks.run_laplace_span_historical_backfill'
    )
      return;
    getLaplaceBackfillAssets({ adapter_id: 'laplaceid' })
      .then((r) => {
        const codes = r.asset_codes || [];
        setLaplaceBackfillAssets(codes);
        setLaplaceBackfillSelected(codes);
      })
      .catch(() => {
        setLaplaceBackfillAssets([]);
        setLaplaceBackfillSelected([]);
      });
  }, [isSuperuser, runOnDemandModalOpen, runOnDemandTask]);

  const closeRunOnDemandModal = () => setRunOnDemandModalOpen(false);

  const submitErhParseFromModal = async () => {
    setErhParseError(null);
    setErhParseOutcome(null);
    if (erhParseFiles.length === 0) {
      setErhParseError('Choose at least one PDF file.');
      return;
    }
    setRunOnDemandLoading(true);
    setError(null);
    try {
      const { task_id } = await queueErhParseInvoicePdf(erhParseFiles, erhParseSessionId);
      for (let i = 0; i < 120; i += 1) {
        await new Promise((r) => setTimeout(r, 2000));
        const st = await getErhTaskStatus(task_id);
        if (!st.ready) continue;
        if (!st.successful) {
          const r = st.result as Record<string, unknown> | undefined;
          const errObj = r?.error as { message?: string } | undefined;
          const msg =
            errObj?.message ||
            (typeof r?.error === 'string' ? r.error : null) ||
            (r?.message as string | undefined) ||
            JSON.stringify(r) ||
            'Task failed';
          throw new Error(msg);
        }
        setErhParseOutcome((st.result as Record<string, unknown>) || {});
        return;
      }
      throw new Error('Timed out waiting for parse task');
    } catch (err) {
      setErhParseError(err instanceof Error ? err.message : 'Parse failed');
    } finally {
      setRunOnDemandLoading(false);
    }
  };

  const submitRunOnDemand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (runOnDemandTask === ERH_PARSE_TASK) {
      await submitErhParseFromModal();
      return;
    }
    setRunOnDemandLoading(true);
    setError(null);
    try {
      // Fusion Solar wizards: dedicated API for adapter/account/assets/dates (backfill vs OEM daily KPI only)
      if (isFusionSolarWizardTask(runOnDemandTask)) {
        if (runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK) {
          if (!fsBackfillDateFrom.trim() || !fsBackfillDateTo.trim()) {
            setError('date_from and date_to are required');
            setRunOnDemandLoading(false);
            return;
          }
        } else {
          if (!fsOemMonthFrom.trim() || !fsOemMonthTo.trim()) {
            setError('From month and To month are required');
            setRunOnDemandLoading(false);
            return;
          }
          if (fsOemMonthFrom.trim() > fsOemMonthTo.trim()) {
            setError('To month must be on or after from month');
            setRunOnDemandLoading(false);
            return;
          }
        }
        if (fsBackfillSelected.length === 0) {
          setError(
            runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK
              ? 'Select at least one asset to run backfill'
              : 'Select at least one asset for OEM daily KPI sync',
          );
          setRunOnDemandLoading(false);
          return;
        }
        const fsPayload = {
          asset_codes: [...fsBackfillSelected],
          date_from:
            runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK
              ? fsBackfillDateFrom.trim()
              : fsOemMonthFrom.trim(),
          date_to:
            runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK ? fsBackfillDateTo.trim() : fsOemMonthTo.trim(),
          adapter_id: fsAdapterId,
          adapter_account_id: typeof fsAccountId === 'number' ? fsAccountId : null,
          ...(notifyEmailOnTaskCompletion ? { send_completion_email: true as const } : {}),
        };
        if (runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK) {
          await runFusionSolarBackfill(fsPayload);
        } else {
          await runFusionSolarOemDailyKpiRun(fsPayload);
        }
        closeRunOnDemandModal();
        return;
      }

      if (runOnDemandTask === KPI_COMPUTE_TASK) {
        if (!kpiDateFrom.trim() || !kpiDateTo.trim()) {
          setError('From date and To date are required');
          setRunOnDemandLoading(false);
          return;
        }
        if (kpiDateFrom.trim() > kpiDateTo.trim()) {
          setError('End date must be on or after start date');
          setRunOnDemandLoading(false);
          return;
        }
        if (kpiAssetsLoaded && kpiAssets.length > 0 && kpiSelectedAssets.length === 0) {
          setError('Select at least one asset, or use Select all');
          setRunOnDemandLoading(false);
          return;
        }
        const allKpiSelected =
          kpiAssets.length > 0 &&
          kpiSelectedAssets.length === kpiAssets.length &&
          kpiAssets.every((c) => kpiSelectedAssets.includes(c));
        const payload: Parameters<typeof runTaskOnDemand>[0] = {
          task: KPI_COMPUTE_TASK,
          args: '[]',
          kwargs: '{}',
          queue: undefined,
          date_from: kpiDateFrom.trim(),
          date_to: kpiDateTo.trim(),
          ...(notifyEmailOnTaskCompletion ? { send_completion_email: true as const } : {}),
        };
        if (kpiAssets.length > 0 && kpiSelectedAssets.length > 0 && !allKpiSelected) {
          payload.asset_codes = [...kpiSelectedAssets];
        }
        await runTaskOnDemand(payload);
        closeRunOnDemandModal();
        return;
      }

      let kwargs = runOnDemandKwargs;
      if (runOnDemandTask === 'data_collection.tasks.run_solargis_daily_ingest') {
        try {
          const parsed = JSON.parse(runOnDemandKwargs || '{}');
          if (typeof parsed !== 'object' || parsed === null) throw new Error('Invalid');
          if (solargisDateFrom.trim()) parsed.date_from = solargisDateFrom.trim();
          if (solargisDateTo.trim()) parsed.date_to = solargisDateTo.trim();
          kwargs = JSON.stringify(parsed);
        } catch {
          const obj: Record<string, string> = {};
          if (solargisDateFrom.trim()) obj.date_from = solargisDateFrom.trim();
          if (solargisDateTo.trim()) obj.date_to = solargisDateTo.trim();
          kwargs = Object.keys(obj).length ? JSON.stringify(obj) : runOnDemandKwargs;
        }
      }
      if (runOnDemandTask === 'data_collection.tasks.run_data_acquisition_30min' && replaceAllDayData30Min) {
        try {
          const parsed = JSON.parse(kwargs || '{}');
          if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('Invalid');
          (parsed as Record<string, unknown>).replace_all_day_data = true;
          kwargs = JSON.stringify(parsed);
        } catch {
          kwargs = JSON.stringify({ replace_all_day_data: true });
        }
      }
      if (runOnDemandTask === 'data_collection.tasks.run_data_acquisition_30min') {
        const rawDays = (durationDays30Min || '').trim();
        if (rawDays) {
          const parsedDays = Number.parseInt(rawDays, 10);
          if (!Number.isFinite(parsedDays) || parsedDays <= 0) {
            setError('Duration days must be a positive integer');
            setRunOnDemandLoading(false);
            return;
          }
          try {
            const parsed = JSON.parse(kwargs || '{}');
            if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('Invalid');
            (parsed as Record<string, unknown>).duration_days = parsedDays;
            kwargs = JSON.stringify(parsed);
          } catch {
            kwargs = JSON.stringify({ duration_days: parsedDays });
          }
        }
      }
      if (runOnDemandTask === 'data_collection.tasks.run_data_acquisition_hourly') {
        const rawDays = (hourlyDurationDays || '').trim();
        if (rawDays) {
          const parsedDays = Number.parseInt(rawDays, 10);
          if (!Number.isFinite(parsedDays) || parsedDays <= 0) {
            setError('Duration days must be a positive integer');
            setRunOnDemandLoading(false);
            return;
          }
          try {
            const parsed = JSON.parse(kwargs || '{}');
            if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('Invalid');
            (parsed as Record<string, unknown>).duration_days = parsedDays;
            kwargs = JSON.stringify(parsed);
          } catch {
            kwargs = JSON.stringify({ duration_days: parsedDays });
          }
        }
      }
      if (runOnDemandTask === 'data_collection.tasks.run_laplace_span_historical_backfill') {
        if (!laplaceSpanDateFrom.trim() || !laplaceSpanDateTo.trim()) {
          setError('From date and To date are required');
          setRunOnDemandLoading(false);
          return;
        }
        if (laplaceBackfillSelected.length === 0) {
          setError('Select at least one Laplace asset');
          setRunOnDemandLoading(false);
          return;
        }
        try {
          const parsed = JSON.parse(kwargs || '{}');
          if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('Invalid');
          (parsed as Record<string, unknown>).date_from = laplaceSpanDateFrom.trim();
          (parsed as Record<string, unknown>).date_to = laplaceSpanDateTo.trim();
          (parsed as Record<string, unknown>).asset_codes = [...laplaceBackfillSelected];
          kwargs = JSON.stringify(parsed);
        } catch {
          kwargs = JSON.stringify({
            date_from: laplaceSpanDateFrom.trim(),
            date_to: laplaceSpanDateTo.trim(),
            asset_codes: [...laplaceBackfillSelected],
          });
        }
      }
      const payload: Parameters<typeof runTaskOnDemand>[0] = {
        task: runOnDemandTask,
        args: runOnDemandArgs,
        kwargs,
        queue: runOnDemandQueue.trim() || undefined,
        ...(notifyEmailOnTaskCompletion ? { send_completion_email: true as const } : {}),
      };
      if (runOnDemandTask === 'data_collection.tasks.run_solargis_daily_ingest') {
        if (solargisDateFrom.trim()) payload.date_from = solargisDateFrom.trim();
        if (solargisDateTo.trim()) payload.date_to = solargisDateTo.trim();
        const allSelected =
          solargisSourceAssets.length > 0 &&
          solargisSelectedAssets.length === solargisSourceAssets.length &&
          solargisSourceAssets.every((c) => solargisSelectedAssets.includes(c));
        if (solargisSourceAssets.length > 0) {
          if (solargisSelectedAssets.length === 0) payload.asset_codes = [];
          else if (!allSelected) payload.asset_codes = [...solargisSelectedAssets];
        }
      }
      await runTaskOnDemand(payload);
      closeRunOnDemandModal();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run task failed');
    } finally {
      setRunOnDemandLoading(false);
    }
  };

  const remove = async (job: BackgroundJob) => {
    // eslint-disable-next-line no-alert
    const ok = window.confirm(`Delete background job "${job.name}"?`);
    if (!ok) return;
    setError(null);
    try {
      await deleteBackgroundJob(job.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  };

  if (!isSuperuser) {
    return (
      <div className="container py-4">
        <h2 className="mb-2">Background Jobs</h2>
        <div className="alert alert-danger">Access denied. Superuser only.</div>
      </div>
    );
  }

  return (
    <div className="container py-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h2 className="mb-1">Background Jobs</h2>
          <div className="text-muted">Manage Celery periodic schedules (django-celery-beat).</div>
        </div>
        <div className="d-flex gap-2">
          <label className={`btn btn-outline-secondary mb-0 ${uploadingImport ? 'disabled' : ''}`}>
            {uploadingImport ? 'Importing…' : 'Upload schedules JSON'}
            <input
              type="file"
              accept=".json,application/json"
              hidden
              disabled={uploadingImport}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  void handleImportSchedulesFile(file);
                }
                e.currentTarget.value = '';
              }}
            />
          </label>
          <div className="form-check d-flex align-items-center ms-1">
            <input
              id="replace-existing-import"
              className="form-check-input mt-0"
              type="checkbox"
              checked={replaceExistingOnImport}
              onChange={(e) => setReplaceExistingOnImport(e.target.checked)}
            />
            <label className="form-check-label ms-2 small text-muted" htmlFor="replace-existing-import">
              Replace existing
            </label>
          </div>
          <button className="btn btn-outline-secondary" onClick={() => void refresh()} disabled={loading}>
            Refresh
          </button>
          <button
            className="btn btn-outline-secondary"
            onClick={() => downloadAllSchedulesAndTasks().catch((e) => setError(e instanceof Error ? e.message : 'Download failed'))}
            title="Download all schedules and task names as JSON"
          >
            Download all schedules and tasks
          </button>
          <button className="btn btn-primary" onClick={openCreate}>
            + New Job
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {importSummary && <div className="alert alert-success">{importSummary}</div>}
      {loading && <div className="alert alert-info">Loading…</div>}

      <div className="form-check mb-3">
        <input
          id="notify-task-completion-email"
          className="form-check-input"
          type="checkbox"
          checked={notifyEmailOnTaskCompletion}
          onChange={(e) => setNotifyEmailOnTaskCompletion(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="notify-task-completion-email">
          Email me when a task I start from this page finishes (success, partial, or failure). Uses your account email;
          requires working SMTP settings.
        </label>
      </div>

      <div className="card border-success">
        <div className="card-header bg-success bg-opacity-10">
          <h5 className="mb-0">Fusion Solar (on demand)</h5>
          <small className="text-muted">
            Historical 5-minute backfill is separate from OEM daily KPI sync (getDevKpiDay →{' '}
            <code>kpis.oem_daily_product_kwh</code>). Use the second button when you only need OEM daily values without
            long-running timeseries collection.
          </small>
        </div>
        <div className="card-body d-flex flex-wrap gap-2">
          <button
            type="button"
            className="btn btn-success"
            onClick={() => openRunOnDemand(FUSION_SOLAR_BACKFILL_TASK)}
          >
            Run data collection (5-min backfill)…
          </button>
          <button
            type="button"
            className="btn btn-outline-success"
            onClick={() => openRunOnDemand(FUSION_SOLAR_OEM_DAILY_TASK)}
          >
            Run OEM daily KPI sync only…
          </button>
        </div>
      </div>

      <div className="card mt-3">
        <div className="table-responsive">
          <table className="table table-striped mb-0">
            <thead>
              <tr>
                <th style={{ minWidth: 220 }}>Name</th>
                <th style={{ minWidth: 260 }}>Task</th>
                <th style={{ minWidth: 160 }}>Schedule</th>
                <th>Queue</th>
                <th>Enabled</th>
                <th style={{ minWidth: 220 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedJobs.map((job) => (
                <tr key={job.id}>
                  <td className="fw-bold">{job.name}</td>
                  <td>
                    <code>{job.task}</code>
                  </td>
                  <td>{scheduleSummary(job)}</td>
                  <td>{job.queue || '-'}</td>
                  <td>{job.enabled ? 'Yes' : 'No'}</td>
                  <td className="d-flex gap-2 flex-wrap">
                    <button className="btn btn-sm btn-outline-primary" onClick={() => openEdit(job)}>
                      Edit
                    </button>
                    <button className="btn btn-sm btn-outline-secondary" onClick={() => void toggleEnabled(job)}>
                      {job.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button className="btn btn-sm btn-outline-success" onClick={() => void runNow(job)}>
                      Run now
                    </button>
                    <button className="btn btn-sm btn-outline-danger" onClick={() => void remove(job)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && sortedJobs.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-muted">
                    No jobs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card mt-4">
        <div className="card-header">
          <h5 className="mb-0">Run task on demand</h5>
          <small className="text-muted">Run any Celery task immediately without a schedule</small>
        </div>
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-striped mb-0">
              <thead>
                <tr>
                  <th style={{ minWidth: 320 }}>Task</th>
                  <th style={{ minWidth: 120 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {runOnDemandTaskOptions.map((t) => (
                  <tr key={t}>
                    <td>
                      <code>{t}</code>
                    </td>
                    <td>
                      <button className="btn btn-sm btn-outline-success" onClick={() => openRunOnDemand(t)}>
                        Run now
                      </button>
                    </td>
                  </tr>
                ))}
                {runOnDemandTaskOptions.length === 0 && !loading && (
                  <tr>
                    <td colSpan={2} className="text-muted">
                      No tasks found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* modal */}
      {modalOpen && (
        <>
          <div
            className="modal-backdrop fade show"
            style={{ zIndex: 1050 }}
            onClick={closeModal}
          />
          <div
            className="modal fade show"
            style={{ display: 'block', zIndex: 1055 }}
            role="dialog"
            aria-modal="true"
            onClick={closeModal}
          >
            <div className="modal-dialog modal-lg" onClick={(e) => e.stopPropagation()}>
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">{editing ? 'Edit Background Job' : 'Create Background Job'}</h5>
                  <button type="button" className="btn-close" onClick={closeModal} />
                </div>
                <form onSubmit={submit}>
                  <div className="modal-body">
                  <div className="row">
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold">Name</label>
                      <input className="form-control" value={name} onChange={(e) => setName(e.target.value)} required />
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold">Enabled</label>
                      <select
                        className="form-select"
                        value={enabled ? 'yes' : 'no'}
                        onChange={(e) => setEnabled(e.target.value === 'yes')}
                      >
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </div>
                    <div className="col-12 mb-3">
                      <label className="form-label fw-bold">Task</label>
                      <input
                        className="form-control"
                        value={task}
                        onChange={(e) => setTask(e.target.value)}
                        list="celery-task-options"
                        required
                      />
                      <datalist id="celery-task-options">
                        {taskOptions.map((t) => (
                          <option key={t} value={t} />
                        ))}
                      </datalist>
                      <div className="form-text">Example: <code>data_collection.tasks.run_data_acquisition</code></div>
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold">Queue (optional)</label>
                      <input className="form-control" value={queue} onChange={(e) => setQueue(e.target.value)} />
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold">Schedule type</label>
                      <select
                        className="form-select"
                        value={scheduleType}
                        onChange={(e) => setScheduleType(e.target.value as 'interval' | 'crontab')}
                      >
                        <option value="interval">Interval</option>
                        <option value="crontab">Crontab</option>
                      </select>
                    </div>
                  </div>

                  {scheduleType === 'interval' ? (
                    <div className="mb-3">
                      <label className="form-label fw-bold">Interval seconds</label>
                      <input
                        type="number"
                        className="form-control"
                        value={intervalSeconds}
                        onChange={(e) => setIntervalSeconds(parseInt(e.target.value || '0', 10))}
                        min={1}
                        required
                      />
                    </div>
                  ) : (
                    <div className="row">
                      <div className="col-md-6 mb-3">
                        <label className="form-label fw-bold">Minute</label>
                        <input className="form-control" value={crontab.minute} onChange={(e) => setCrontab({ ...crontab, minute: e.target.value })} />
                      </div>
                      <div className="col-md-6 mb-3">
                        <label className="form-label fw-bold">Hour</label>
                        <input className="form-control" value={crontab.hour} onChange={(e) => setCrontab({ ...crontab, hour: e.target.value })} />
                      </div>
                      <div className="col-md-4 mb-3">
                        <label className="form-label fw-bold">Day of week</label>
                        <input className="form-control" value={crontab.day_of_week} onChange={(e) => setCrontab({ ...crontab, day_of_week: e.target.value })} />
                      </div>
                      <div className="col-md-4 mb-3">
                        <label className="form-label fw-bold">Day of month</label>
                        <input className="form-control" value={crontab.day_of_month} onChange={(e) => setCrontab({ ...crontab, day_of_month: e.target.value })} />
                      </div>
                      <div className="col-md-4 mb-3">
                        <label className="form-label fw-bold">Month of year</label>
                        <input className="form-control" value={crontab.month_of_year} onChange={(e) => setCrontab({ ...crontab, month_of_year: e.target.value })} />
                      </div>
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="form-label fw-bold">Args (JSON)</label>
                    <textarea className="form-control" rows={3} value={args} onChange={(e) => setArgs(e.target.value)} />
                  </div>
                  <div className="mb-3">
                    <label className="form-label fw-bold">Kwargs (JSON)</label>
                    <textarea className="form-control" rows={4} value={kwargs} onChange={(e) => setKwargs(e.target.value)} />
                  </div>
                  <div className="mb-3">
                    <label className="form-label fw-bold">Description (optional)</label>
                    <input className="form-control" value={description} onChange={(e) => setDescription(e.target.value)} />
                  </div>
                  </div>
                  <div className="modal-footer">
                    <button type="button" className="btn btn-secondary" onClick={closeModal} disabled={saving}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={saving}>
                      {saving ? 'Saving…' : 'Save'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Run on demand modal */}
      {runOnDemandModalOpen && (
        <>
          <div
            className="modal-backdrop fade show"
            style={{ zIndex: 1050 }}
            onClick={closeRunOnDemandModal}
          />
          <div
            className="modal fade show"
            style={{ display: 'block', zIndex: 1055 }}
            role="dialog"
            aria-modal="true"
            onClick={closeRunOnDemandModal}
          >
            <div
              className={`modal-dialog${isFusionSolarWizardTask(runOnDemandTask) ? ' modal-lg' : ''}`}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-content">
                <div className="modal-header">
                  <div>
                    <h5 className="modal-title">
                      {runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK
                        ? 'Data collection'
                        : runOnDemandTask === FUSION_SOLAR_OEM_DAILY_TASK
                          ? 'OEM daily KPI sync'
                          : 'Run task on demand'}
                    </h5>
                    {isFusionSolarWizardTask(runOnDemandTask) && (
                      <p className="text-muted small mb-0 mt-1">
                        {runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK
                          ? 'Fusion Solar is selected by default. Choose account, collection period, and sites.'
                          : 'Inverters only (Huawei devTypeId 1). Writes oem_daily_product_kwh (updates or creates kpis row per device/day); no 5-minute backfill.'}
                      </p>
                    )}
                  </div>
                  <button type="button" className="btn-close" onClick={closeRunOnDemandModal} />
                </div>
                <form onSubmit={submitRunOnDemand}>
                  <div className="modal-body">
                    <p className="text-muted small mb-3">
                      {isFusionSolarWizardTask(runOnDemandTask)
                        ? 'The task is queued and runs in the background.'
                        : 'The task runs immediately regardless of time (for testing or re-acquisition).'}
                    </p>
                    <div className="mb-3">
                      <label className="form-label fw-bold">Task</label>
                      <input className="form-control" value={runOnDemandTask} readOnly disabled />
                    </div>
                    {runOnDemandTask !== ERH_PARSE_TASK && (
                      <div className="form-check mb-3">
                        <input
                          id="modal-notify-task-completion"
                          className="form-check-input"
                          type="checkbox"
                          checked={notifyEmailOnTaskCompletion}
                          onChange={(e) => setNotifyEmailOnTaskCompletion(e.target.checked)}
                        />
                        <label className="form-check-label small" htmlFor="modal-notify-task-completion">
                          Email me when this task finishes (same as the checkbox above the jobs list).
                        </label>
                      </div>
                    )}
                    {runOnDemandTask === ERH_PARSE_TASK && (
                      <div className="mb-3">
                        <div className="alert alert-info py-2 mb-2">
                          Choose one or more PDFs to parse on the Celery worker (same pipeline as Energy Revenue Hub → Parse PDF
                          async). Optional billing session ID attaches parsed rows to that session. Close the modal when you have
                          validated the table.
                        </div>
                        <label className="form-label fw-bold">PDF file(s)</label>
                        <input
                          type="file"
                          accept=".pdf,application/pdf"
                          multiple
                          className="form-control"
                          onChange={(e) => setErhParseFiles(Array.from(e.target.files || []))}
                        />
                        {erhParseFiles.length > 0 && (
                          <p className="small text-muted mb-2 mt-1">
                            {erhParseFiles.length} file(s) selected: {erhParseFiles.map((f) => f.name).join(', ')}
                          </p>
                        )}
                        <label className="form-label fw-bold mt-2">Billing session ID (optional)</label>
                        <input
                          className="form-control font-monospace"
                          value={erhParseSessionId}
                          onChange={(e) => setErhParseSessionId(e.target.value)}
                          placeholder="e.g. uuid from Energy Revenue Hub session"
                          autoComplete="off"
                        />
                        {erhParseError && (
                          <div className="alert alert-danger mt-2 py-2 mb-0" role="alert">
                            {erhParseError}
                          </div>
                        )}
                        {erhParseOutcome && (
                          <div className="mt-3">
                            <h6 className="mb-2">Parse result</h6>
                            {Array.isArray(erhParseOutcome.results) && erhParseOutcome.results.length > 0 ? (
                              <div className="table-responsive">
                                <table className="table table-sm table-bordered mb-2">
                                  <thead>
                                    <tr>
                                      <th>#</th>
                                      <th>Invoice #</th>
                                      <th>Date</th>
                                      <th>Export kWh</th>
                                      <th>Vendor</th>
                                      <th>Errors</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {(erhParseOutcome.results as Record<string, unknown>[]).map((row, i) => (
                                      <tr key={i}>
                                        <td>{i + 1}</td>
                                        <td>{String(row.invoice_number ?? '')}</td>
                                        <td>{String(row.invoice_date ?? '')}</td>
                                        <td>{String(row.export_energy_kwh ?? row.export_energy ?? '')}</td>
                                        <td>{String(row.vendor ?? '')}</td>
                                        <td className="small">
                                          {Array.isArray(row.errors) ? (row.errors as string[]).join('; ') : String(row.errors ?? '')}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <p className="text-muted small">No results array in task payload (see raw JSON below).</p>
                            )}
                            <details className="small">
                              <summary className="text-muted">Raw task result (JSON)</summary>
                              <pre
                                className="bg-light border rounded p-2 mt-1 mb-0"
                                style={{ maxHeight: 'min(240px, 40vh)', overflow: 'auto' }}
                              >
                                {JSON.stringify(erhParseOutcome, null, 2)}
                              </pre>
                            </details>
                          </div>
                        )}
                      </div>
                    )}
                    {runOnDemandTask === KPI_COMPUTE_TASK && (
                      <div className="mb-3">
                        <div className="alert alert-info py-2 mb-2">
                          Compute daily KPI rows for selected sites and local calendar date range. Uses the default Celery queue.
                        </div>
                        {!kpiAssetsLoaded && (
                          <p className="text-muted small mb-0">Loading assets…</p>
                        )}
                        {kpiAssetsLoaded && kpiAssets.length === 0 && (
                          <p className="text-warning small mb-2">No assets found in Asset List.</p>
                        )}
                        {kpiAssets.length > 0 && (
                          <>
                            <label className="form-label small fw-bold">Assets ({kpiSelectedAssets.length} selected)</label>
                            <div className="d-flex flex-wrap gap-2 mb-2">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => setKpiSelectedAssets([...kpiAssets])}
                              >
                                Select all
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => setKpiSelectedAssets([])}
                              >
                                Deselect all
                              </button>
                            </div>
                            <div
                              className="border rounded p-2 bg-light mb-3"
                              style={{ maxHeight: 'min(320px, 45vh)', overflowY: 'auto' }}
                            >
                              {kpiAssets.map((code) => (
                                <div key={code} className="form-check">
                                  <input
                                    id={`kpi-asset-${code}`}
                                    type="checkbox"
                                    className="form-check-input"
                                    checked={kpiSelectedAssets.includes(code)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setKpiSelectedAssets((prev) => (prev.includes(code) ? prev : [...prev, code].sort()));
                                      } else {
                                        setKpiSelectedAssets((prev) => prev.filter((c) => c !== code));
                                      }
                                    }}
                                  />
                                  <label className="form-check-label" htmlFor={`kpi-asset-${code}`}>
                                    {code}
                                  </label>
                                </div>
                              ))}
                            </div>
                          </>
                        )}
                        <div className="row g-2">
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">From date</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={kpiDateFrom}
                              onChange={(e) => setKpiDateFrom(e.target.value)}
                            />
                          </div>
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">To date</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={kpiDateTo}
                              onChange={(e) => setKpiDateTo(e.target.value)}
                            />
                          </div>
                        </div>
                        <span className="small text-muted d-block mt-1">
                          Each day in the range is interpreted as a local calendar day per asset (same labels for all sites).
                        </span>
                      </div>
                    )}
                    {runOnDemandTask === 'data_collection.tasks.run_solargis_daily_ingest' && (
                      <div className="mb-3">
                        <div className="alert alert-info py-2 mb-0">
                          On-demand mode will process selected source assets regardless of schedule.
                          Ensure the Solargis adapter is <strong>Enabled</strong> in Data Collection for each source asset.
                        </div>
                        {!solargisSourceAssetsLoaded && (
                          <p className="text-muted small mt-2 mb-0">
                            Loading configured source assets…
                          </p>
                        )}
                        {solargisSourceAssetsLoaded && solargisSourceAssets.length === 0 && (
                          <p className="text-warning small mt-2 mb-0">
                            No Solargis source assets configured. Add and enable the Solargis adapter in Data Collection for the source sites.
                          </p>
                        )}
                        {solargisSourceAssets.length > 0 && (
                          <div className="mt-2">
                            <label className="form-label small fw-bold">
                              Source assets to run
                              {solargisAllConfiguredCount != null && solargisAllConfiguredCount > solargisSourceAssets.length ? (
                                <span className="text-muted fw-normal"> ({solargisSourceAssets.length} of {solargisAllConfiguredCount} configured)</span>
                              ) : (
                                <span className="text-muted fw-normal"> ({solargisSourceAssets.length})</span>
                              )}
                            </label>
                            {solargisAllConfiguredCount != null && solargisAllConfiguredCount > solargisSourceAssets.length && (
                              <p className="small text-muted mb-1 mt-0">
                                {solargisAllConfiguredCount - solargisSourceAssets.length} site(s) use another site&apos;s satellite data and do not run the ingest.
                              </p>
                            )}
                            <div className="d-flex flex-wrap gap-2 mb-2 align-items-center">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => setSolargisSelectedAssets([...solargisSourceAssets])}
                              >
                                Select all
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => setSolargisSelectedAssets([])}
                              >
                                Deselect all
                              </button>
                              <span className="small align-self-center">
                                {solargisSelectedAssets.length === 0 ? (
                                  <span className="text-danger">Select at least one asset to run.</span>
                                ) : (
                                  <span className="text-muted">
                                    {solargisSelectedAssets.length} of {solargisSourceAssets.length} selected
                                  </span>
                                )}
                              </span>
                            </div>
                            <div
                              className="border rounded p-2 bg-light"
                              style={{ maxHeight: 'min(400px, 50vh)', overflowY: 'auto' }}
                              role="list"
                              aria-label={`${solargisSourceAssets.length} configured Solargis source assets`}
                            >
                              {solargisSourceAssets.map((code) => (
                                <div key={code} className="form-check">
                                  <input
                                    id={`solargis-asset-${code}`}
                                    type="checkbox"
                                    className="form-check-input"
                                    checked={solargisSelectedAssets.includes(code)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSolargisSelectedAssets((prev) => (prev.includes(code) ? prev : [...prev, code]));
                                      } else {
                                        setSolargisSelectedAssets((prev) => prev.filter((c) => c !== code));
                                      }
                                    }}
                                  />
                                  <label className="form-check-label" htmlFor={`solargis-asset-${code}`}>
                                    {code}
                                  </label>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="row g-2 mt-2">
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">Start date (optional)</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={solargisDateFrom}
                              onChange={(e) => setSolargisDateFrom(e.target.value)}
                            />
                            <span className="small text-muted">Leave empty for default (last 3 days)</span>
                          </div>
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">End date (optional)</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={solargisDateTo}
                              onChange={(e) => setSolargisDateTo(e.target.value)}
                            />
                            <span className="small text-muted">Leave empty for default</span>
                          </div>
                        </div>
                        {solargisDailyApiCalls !== null && (
                          <div className="alert alert-warning py-2 mt-2 mb-0">
                            Solargis API calls today: <strong>{solargisDailyApiCalls}</strong>
                            {solargisDailyApiCalls === 0 && (
                              <span className="d-block small mt-1 text-muted">
                                (No ingest runs have made API calls yet, or no Solargis source assets are configured.)
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    {isFusionSolarWizardTask(runOnDemandTask) && (
                      <div className="mb-3">
                        <div className="alert alert-info py-2 mb-2">
                          {runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK ? (
                            <>Choose adapter account and the date range to collect. Then pick which sites to include.</>
                          ) : (
                            <>
                              Choose adapter account and <strong>from / to month</strong>. One <code>getDevKpiDay</code>{' '}
                              call per month (collectTime = month start, ms); the response lists daily points. Applies only
                              to devices with <code>device_type_id = 1</code> (string inverters). Sets{' '}
                              <code>oem_daily_product_kwh</code> on each <code>device_id</code> + <code>day_date</code>{' '}
                              (updates existing rows or inserts a minimal row; internal KPI columns may be filled later by{' '}
                              <code>compute_daily_kpis_previous_day</code>).
                            </>
                          )}
                        </div>
                        <div className="row g-2 mb-2">
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">Adapter</label>
                            <select
                              className="form-select form-select-sm"
                              value={fsAdapterId}
                              onChange={(e) => {
                                setFsAdapterId(e.target.value);
                                setFsAccountId('');
                              }}
                            >
                              <option value="fusion_solar">Fusion Solar (Huawei)</option>
                            </select>
                          </div>
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">Adapter account</label>
                            <select
                              className="form-select form-select-sm"
                              value={fsAccountId === '' ? '' : String(fsAccountId)}
                              onChange={(e) => {
                                const v = e.target.value;
                                setFsAccountId(v ? Number(v) : '');
                              }}
                            >
                              <option value="">All accounts</option>
                              {fsAccounts.map((acc) => (
                                <option key={acc.id} value={acc.id}>
                                  {acc.name || `${acc.adapter_id} #${acc.id}`}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                        {runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK ? (
                          <div className="row g-2 mb-3">
                            <div className="col-md-6">
                              <label className="form-label small fw-bold">Collect from (date)</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={fsBackfillDateFrom}
                                onChange={(e) => setFsBackfillDateFrom(e.target.value)}
                              />
                            </div>
                            <div className="col-md-6">
                              <label className="form-label small fw-bold">Collect through (date)</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={fsBackfillDateTo}
                                onChange={(e) => setFsBackfillDateTo(e.target.value)}
                              />
                            </div>
                          </div>
                        ) : (
                          <div className="row g-2 mb-3">
                            <div className="col-md-6">
                              <label className="form-label small fw-bold">From month</label>
                              <input
                                type="month"
                                className="form-control form-control-sm"
                                value={fsOemMonthFrom}
                                onChange={(e) => setFsOemMonthFrom(e.target.value)}
                              />
                            </div>
                            <div className="col-md-6">
                              <label className="form-label small fw-bold">To month</label>
                              <input
                                type="month"
                                className="form-control form-control-sm"
                                value={fsOemMonthTo}
                                onChange={(e) => setFsOemMonthTo(e.target.value)}
                              />
                            </div>
                          </div>
                        )}
                        <div className="col-12 px-0">
                          <label className="form-label small fw-bold">Sites to collect</label>
                          <div
                            className="border rounded p-2 bg-light"
                            style={{ maxHeight: 'min(300px, 40vh)', overflowY: 'auto' }}
                          >
                            {fsBackfillAssets.length === 0 ? (
                              <span className="text-muted small">No assets for this adapter/account.</span>
                            ) : (
                              fsBackfillAssets.map((code) => (
                                <div key={code} className="form-check">
                                  <input
                                    id={`fs-asset-${code}`}
                                    type="checkbox"
                                    className="form-check-input"
                                    checked={fsBackfillSelected.includes(code)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setFsBackfillSelected((prev) =>
                                          prev.includes(code) ? prev : [...prev, code].sort()
                                        );
                                      } else {
                                        setFsBackfillSelected((prev) => prev.filter((c) => c !== code));
                                      }
                                    }}
                                  />
                                  <label className="form-check-label" htmlFor={`fs-asset-${code}`}>
                                    {code}
                                  </label>
                                </div>
                              ))
                            )}
                          </div>
                          <div className="d-flex justify-content-between mt-1">
                            <small className="text-muted">{fsBackfillSelected.length} selected.</small>
                            {fsBackfillAssets.length > 0 && (
                              <div className="btn-group btn-group-sm">
                                <button
                                  type="button"
                                  className="btn btn-outline-secondary"
                                  onClick={() => setFsBackfillSelected([...fsBackfillAssets])}
                                >
                                  All
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-outline-secondary"
                                  onClick={() => setFsBackfillSelected([])}
                                >
                                  None
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    {runOnDemandTask === 'data_collection.tasks.run_data_acquisition_30min' && (
                      <div className="mb-3">
                        <div className="alert alert-warning py-2 mb-2">
                          For Laplace daily.php metrics, replace all points for the queried local day (scoped by
                          <code> oem_metric </code>) before writing new rows.
                        </div>
                        <label className="form-label small fw-bold">Duration (calendar days, optional)</label>
                        <input
                          type="number"
                          className="form-control form-control-sm mb-2"
                          min={1}
                          max={7}
                          value={durationDays30Min}
                          onChange={(e) => setDurationDays30Min(e.target.value)}
                          placeholder="e.g. 3"
                        />
                        <span className="small text-muted d-block mb-2">
                          If set, 30-min backfill runs day-by-day for the selected local date duration.
                        </span>
                        <div className="form-check">
                          <input
                            id="replace-all-day-30min"
                            type="checkbox"
                            className="form-check-input"
                            checked={replaceAllDayData30Min}
                            onChange={(e) => setReplaceAllDayData30Min(e.target.checked)}
                          />
                          <label className="form-check-label" htmlFor="replace-all-day-30min">
                            Replace all day data (daily.php metrics, oem_metric-scoped)
                          </label>
                        </div>
                      </div>
                    )}
                    {runOnDemandTask === 'data_collection.tasks.run_data_acquisition_hourly' && (
                      <div className="mb-3">
                        <div className="alert alert-warning py-2 mb-2">
                          Optional backfill for Laplace hourly.php (minute unit). If set, the task fetches each hour
                          in the selected calendar-day duration sequentially. Empty means default previous hour only.
                        </div>
                        <label className="form-label small fw-bold">Duration (calendar days, optional)</label>
                        <input
                          type="number"
                          className="form-control form-control-sm"
                          min={1}
                          max={7}
                          value={hourlyDurationDays}
                          onChange={(e) => setHourlyDurationDays(e.target.value)}
                          placeholder="e.g. 3"
                        />
                        <span className="small text-muted">
                          Safety cap is 7 days. Larger values are capped to avoid excessive provider calls.
                        </span>
                      </div>
                    )}
                    {runOnDemandTask === 'data_collection.tasks.run_laplace_span_historical_backfill' && (
                      <div className="mb-3">
                        <div className="alert alert-info py-2 mb-2">
                          Fetch Laplace historical CSV using <code>span.php</code> for selected calendar range.
                        </div>
                        <label className="form-label small fw-bold">Assets</label>
                        <div
                          className="border rounded p-2 bg-light mb-2"
                          style={{ maxHeight: 'min(300px, 40vh)', overflowY: 'auto' }}
                        >
                          {laplaceBackfillAssets.length === 0 ? (
                            <span className="text-muted small">No enabled Laplace assets found.</span>
                          ) : (
                            laplaceBackfillAssets.map((code) => (
                              <div key={code} className="form-check">
                                <input
                                  id={`laplace-span-asset-${code}`}
                                  type="checkbox"
                                  className="form-check-input"
                                  checked={laplaceBackfillSelected.includes(code)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setLaplaceBackfillSelected((prev) =>
                                        prev.includes(code) ? prev : [...prev, code].sort()
                                      );
                                    } else {
                                      setLaplaceBackfillSelected((prev) => prev.filter((c) => c !== code));
                                    }
                                  }}
                                />
                                <label className="form-check-label" htmlFor={`laplace-span-asset-${code}`}>
                                  {code}
                                </label>
                              </div>
                            ))
                          )}
                        </div>
                        {laplaceBackfillAssets.length > 0 && (
                          <div className="d-flex justify-content-between mb-2">
                            <small className="text-muted">{laplaceBackfillSelected.length} selected.</small>
                            <div className="btn-group btn-group-sm">
                              <button
                                type="button"
                                className="btn btn-outline-secondary"
                                onClick={() => setLaplaceBackfillSelected([...laplaceBackfillAssets])}
                              >
                                All
                              </button>
                              <button
                                type="button"
                                className="btn btn-outline-secondary"
                                onClick={() => setLaplaceBackfillSelected([])}
                              >
                                None
                              </button>
                            </div>
                          </div>
                        )}
                        <div className="row g-2">
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">From date</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={laplaceSpanDateFrom}
                              onChange={(e) => setLaplaceSpanDateFrom(e.target.value)}
                            />
                          </div>
                          <div className="col-md-6">
                            <label className="form-label small fw-bold">To date</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={laplaceSpanDateTo}
                              onChange={(e) => setLaplaceSpanDateTo(e.target.value)}
                            />
                          </div>
                        </div>
                        <span className="small text-muted">
                          Range is processed day-by-day per asset and split into smaller asset batches.
                        </span>
                      </div>
                    )}
                    {runOnDemandTask !== KPI_COMPUTE_TASK &&
                      runOnDemandTask !== ERH_PARSE_TASK &&
                      !isFusionSolarWizardTask(runOnDemandTask) && (
                      <>
                        <div className="mb-3">
                          <label className="form-label fw-bold">Args (JSON, optional)</label>
                          <textarea
                            className="form-control font-monospace"
                            rows={2}
                            value={runOnDemandArgs}
                            onChange={(e) => setRunOnDemandArgs(e.target.value)}
                            placeholder="[]"
                          />
                        </div>
                        <div className="mb-3">
                          <label className="form-label fw-bold">Kwargs (JSON, optional)</label>
                          <textarea
                            className="form-control font-monospace"
                            rows={3}
                            value={runOnDemandKwargs}
                            onChange={(e) => setRunOnDemandKwargs(e.target.value)}
                            placeholder="{}"
                          />
                        </div>
                        <div className="mb-3">
                          <label className="form-label fw-bold">Queue (optional)</label>
                          <input
                            className="form-control"
                            value={runOnDemandQueue}
                            onChange={(e) => setRunOnDemandQueue(e.target.value)}
                            placeholder="Leave empty for default"
                          />
                        </div>
                      </>
                    )}
                  </div>
                  <div className="modal-footer">
                    <button type="button" className="btn btn-secondary" onClick={closeRunOnDemandModal} disabled={runOnDemandLoading}>
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn btn-success"
                      disabled={
                        runOnDemandLoading ||
                        (runOnDemandTask === ERH_PARSE_TASK && erhParseFiles.length === 0) ||
                        (runOnDemandTask === KPI_COMPUTE_TASK &&
                          (!kpiAssetsLoaded ||
                            !kpiDateFrom.trim() ||
                            !kpiDateTo.trim() ||
                            kpiDateFrom.trim() > kpiDateTo.trim() ||
                            (kpiAssets.length > 0 && kpiSelectedAssets.length === 0))) ||
                        (runOnDemandTask === 'data_collection.tasks.run_solargis_daily_ingest' &&
                          solargisSourceAssets.length > 0 &&
                          solargisSelectedAssets.length === 0) ||
                        (runOnDemandTask === 'data_collection.tasks.run_laplace_span_historical_backfill' &&
                          (!laplaceSpanDateFrom.trim() ||
                            !laplaceSpanDateTo.trim() ||
                            laplaceBackfillSelected.length === 0)) ||
                        (isFusionSolarWizardTask(runOnDemandTask) &&
                          (runOnDemandTask === FUSION_SOLAR_BACKFILL_TASK
                            ? !fsBackfillDateFrom.trim() ||
                              !fsBackfillDateTo.trim() ||
                              fsBackfillSelected.length === 0
                            : !fsOemMonthFrom.trim() ||
                              !fsOemMonthTo.trim() ||
                              fsOemMonthFrom.trim() > fsOemMonthTo.trim() ||
                              fsBackfillSelected.length === 0))
                      }
                    >
                      {runOnDemandLoading ? 'Running…' : runOnDemandTask === ERH_PARSE_TASK ? 'Run parse' : 'Run task'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

