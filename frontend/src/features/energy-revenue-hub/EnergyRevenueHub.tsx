import { useEffect, useMemo, useState } from 'react';
import JSZip from 'jszip';
import Swal from 'sweetalert2';
import { useTheme } from '../../contexts/ThemeContext';
import { getGradientBg } from '../../utils/themeColors';
import { fetchAssetList } from '../site-onboarding/api';
import type { AssetList } from '../site-onboarding/types';
import {
  createSession,
  fetchEligibleBillingAssets,
  createPayment,
  createUtilityInvoice,
  updateUtilityInvoice,
  freezeAllUtilityInvoices,
  passUtilityInvoice,
  resolveBillingInvoicePdfMerge,
  createMeterReading,
  createAssetGeneration,
  createPenalty,
  createAdjustment,
  deleteAdjustment,
  deleteAssetGeneration,
  deleteMeterReading,
  deletePayment,
  deletePenalty,
  deleteParsedInvoice,
  deleteBillingLineItem,
  deleteGeneratedInvoice,
  deleteUtilityInvoice,
  generateBillingTableAsync,
  recalculateBillingLinesAsync,
  addAssetToBillingSession,
  postInvoice,
  generateInvoiceAsync,
  generateLineItemInvoice,
  getSharepointUploadHealth,
  getTaskStatus,
  testSharepointConnection,
  getSessionDetail,
  listSessions,
  fetchContractProfileKeys,
  parseInvoicePdfAsyncWithUploadProgress,
  unfreezeBillingLines,
  type BillingSession,
  type EligibleBillingAsset,
} from './api';
import { lineGroupKeyForErhLineRow, type SessionDetailBundle, type TabId } from './SessionDataTabs';
import type { ErhPageTab } from './erhTypes';
import { ErhAuditPanel } from './tabs/ErhAuditPanel';
import { ErhBillingPanel } from './tabs/ErhBillingPanel';
import { ErhInvoicePanel } from './tabs/ErhInvoicePanel';
import { ErhParsePanel } from './tabs/ErhParsePanel';
import { ErhSessionTab } from './tabs/ErhSessionTab';
import { ErhWorkspace } from './tabs/ErhWorkspace';

export function EnergyRevenueHub() {
  const SESSION_STORAGE_KEY = 'erh:selectedSessionId';
  const { theme } = useTheme();
  const bgGradient = getGradientBg(theme);
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textMuted = theme === 'dark' ? '#94a3b8' : '#64748b';

  const [sessions, setSessions] = useState<BillingSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [sessionSearch, setSessionSearch] = useState('');
  /** Server-side filters: contract profile key + billing month (YYYY-MM). */
  const [contractTypeFilter, setContractTypeFilter] = useState('');
  const [billingMonthFilter, setBillingMonthFilter] = useState('');
  const [sessionIdLookup, setSessionIdLookup] = useState('');
  const [sessionDetail, setSessionDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');

  const [country, setCountry] = useState('Singapore');
  const [portfolio, setPortfolio] = useState('');
  const [assetCode, setAssetCode] = useState('');
  const [selectedAssetCodes, setSelectedAssetCodes] = useState<string[]>([]);
  const [assetSearch, setAssetSearch] = useState('');
  const [assetOptions, setAssetOptions] = useState<AssetList[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [createContractType, setCreateContractType] = useState('sg_ppa_maiora');
  const [createBillingMonth, setCreateBillingMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [eligibleAssets, setEligibleAssets] = useState<EligibleBillingAsset[]>([]);
  const [eligPickAssetCode, setEligPickAssetCode] = useState('');
  /** Default used for generate / recalculate billing table APIs (export kWh). */
  const defaultExportKwh = 10000;
  const [sessionAddAssetCode, setSessionAddAssetCode] = useState('');
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploadRows, setUploadRows] = useState<
    Array<{
      name: string;
      size: number;
      progress: number;
      status: 'pending' | 'uploading' | 'queued' | 'failed';
      reasonCode?: string;
      reasonMessage?: string;
    }>
  >([]);
  const [securityRejections, setSecurityRejections] = useState<
    Array<{ original_filename?: string; security_reason_code?: string; security_reason_message?: string }>
  >([]);
  const [taskState, setTaskState] = useState<'IDLE' | 'RUNNING' | 'SUCCESS' | 'FAILED'>('IDLE');
  const [uploadHealth, setUploadHealth] = useState<{
    generated: { total: number; on_sharepoint: number; failed: number };
    utility: { uploaded: number; failed: number };
  } | null>(null);
  const [sharepointTestResult, setSharepointTestResult] = useState<string>('');
  const [newUtilityInvoiceNo, setNewUtilityInvoiceNo] = useState('');
  const [newUtilityTotalAmount, setNewUtilityTotalAmount] = useState('');
  const [newPaymentAmount, setNewPaymentAmount] = useState('');
  const [newPaymentInvoiceId, setNewPaymentInvoiceId] = useState('');
  const [newReadingDeviceId, setNewReadingDeviceId] = useState('');
  const [newReadingValue, setNewReadingValue] = useState('');
  const [newAssetGenMonth, setNewAssetGenMonth] = useState('');
  const [newAssetGenKwh, setNewAssetGenKwh] = useState('');
  const [newPenaltyType, setNewPenaltyType] = useState('');
  const [newPenaltyAmount, setNewPenaltyAmount] = useState('');
  const [newAdjustmentType, setNewAdjustmentType] = useState('');
  const [newAdjustmentAmount, setNewAdjustmentAmount] = useState('');
  const [canDelete, setCanDelete] = useState(false);
  const [canUnfreezeBillingLines, setCanUnfreezeBillingLines] = useState(false);
  const [pageTab, setPageTab] = useState<ErhPageTab>('session');
  const [registeredContractKeys, setRegisteredContractKeys] = useState<string[]>([]);
  const [selectedGeneratedIds, setSelectedGeneratedIds] = useState<string[]>([]);
  const [expandedConflictIds, setExpandedConflictIds] = useState<string[]>([]);
  const [generatedDownloadProgress, setGeneratedDownloadProgress] = useState<{
    active: boolean;
    total: number;
    completed: number;
    ok: number;
    failed: number;
    mode: 'zip' | 'files';
  }>({ active: false, total: 0, completed: 0, ok: 0, failed: 0, mode: 'zip' });

  function formatBytes(bytes: number): string {
    if (!Number.isFinite(bytes) || bytes < 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    const gb = mb / 1024;
    return `${gb.toFixed(2)} GB`;
  }

  function formatBillingTableWriteSummary(write: unknown): string {
    if (!write || typeof write !== 'object') return '';
    const w = write as Record<string, unknown>;
    const frozenSkipped = Number(w.frozen_skipped ?? 0);
    const updated = Number(w.updated ?? 0);
    const created = Number(w.created ?? 0);
    const deletedUnfrozen = Number(w.deleted_unfrozen ?? 0);
    const keptFrozenUnmatched = Number(w.kept_frozen_unmatched ?? 0);
    const parts: string[] = [];
    if (frozenSkipped > 0) parts.push(`${frozenSkipped} frozen row(s) unchanged`);
    if (updated > 0) parts.push(`${updated} updated`);
    if (created > 0) parts.push(`${created} added`);
    if (deletedUnfrozen > 0) parts.push(`${deletedUnfrozen} unfrozen row(s) removed`);
    if (keptFrozenUnmatched > 0) parts.push(`${keptFrozenUnmatched} frozen row(s) kept (no computed match)`);
    if (parts.length === 0) return '';
    return ` Persist: ${parts.join('; ')}.`;
  }

  async function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function waitForTask(taskId: string, label: string) {
    for (let i = 0; i < 90; i += 1) {
      const s = await getTaskStatus(taskId);
      if (!s.success) {
        throw new Error(s.message || `${label} status check failed`);
      }
      if (!s.ready) {
        setTaskState('RUNNING');
        setStatusMsg(`${label}: ${s.state}...`);
        await sleep(2000);
        continue;
      }
      if (!s.successful) {
        const msg =
          (s.result as any)?.error?.message ||
          (s.result as any)?.error_message ||
          `${label} failed`;
        throw new Error(msg);
      }
      const raw = (s.result || {}) as Record<string, unknown>;
      // Celery marks the task SUCCESS even when our payload is { success: false, error: ... }.
      if (raw.success === false) {
        const err = raw.error as Record<string, unknown> | string | undefined;
        const msg =
          (typeof err === 'object' && err && typeof err.message === 'string' && err.message) ||
          (typeof err === 'string' ? err : null) ||
          (typeof raw.error_message === 'string' ? raw.error_message : null) ||
          `${label} failed`;
        throw new Error(msg);
      }
      setTaskState('SUCCESS');
      return raw as any;
    }
    setTaskState('FAILED');
    throw new Error(`${label} timed out`);
  }

  const selectedSession = useMemo(
    () => sessions.find((s) => s.id === selectedSessionId) || null,
    [sessions, selectedSessionId]
  );
  const filteredSessions = useMemo(() => {
    const q = sessionSearch.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) =>
      `${s.id} ${s.country} ${s.portfolio} ${s.status} ${s.start_date || ''} ${s.end_date || ''} ${
        s.billing_contract_type || ''
      } ${s.session_label || ''} ${s.billing_month || ''}`
        .toLowerCase()
        .includes(q)
    );
  }, [sessions, sessionSearch]);

  const countryOptions = useMemo(() => {
    return Array.from(new Set(assetOptions.map((a) => (a.country || '').trim()).filter(Boolean))).sort((a, b) =>
      a.localeCompare(b)
    );
  }, [assetOptions]);

  const portfolioOptions = useMemo(() => {
    return Array.from(
      new Set(
        assetOptions
          .filter((a) => !country || a.country === country)
          .map((a) => (a.portfolio || '').trim())
          .filter(Boolean)
      )
    ).sort((a, b) => a.localeCompare(b));
  }, [assetOptions, country]);

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    return assetOptions
      .filter((a) => (!country || a.country === country) && (!portfolio || a.portfolio === portfolio))
      .filter((a) =>
        !q
          ? true
          : `${a.asset_code} ${a.asset_name || ''}`.toLowerCase().includes(q)
      )
      .sort((a, b) => (a.asset_name || a.asset_code).localeCompare(b.asset_name || b.asset_code));
  }, [assetOptions, country, portfolio, assetSearch]);

  const eligibleAssetsFiltered = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    return eligibleAssets
      .filter((a) => (!q ? true : `${a.asset_code} ${a.asset_name}`.toLowerCase().includes(q)))
      .sort((a, b) => a.asset_name.localeCompare(b.asset_name));
  }, [eligibleAssets, assetSearch]);

  const selectedAsset = useMemo(() => filteredAssets.find((a) => a.asset_code === assetCode) || null, [filteredAssets, assetCode]);
  // selected assets (legacy) are no longer used for session creation; keep `selectedAssetCodes`
  // state for other workflow helpers (e.g. default asset for manual creates).

  async function refreshSessions(preserveSelection = true) {
    const res = await listSessions({
      billing_contract_type: contractTypeFilter.trim() || undefined,
      billing_month: billingMonthFilter.trim() || undefined,
    });
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to load sessions');
      return;
    }
    const nextSessions = res.sessions || [];
    setSessions(nextSessions);
    if (!preserveSelection && nextSessions.length > 0) {
      setSelectedSessionId(nextSessions[0].id);
      return;
    }
    if (preserveSelection && selectedSessionId && !nextSessions.some((s) => s.id === selectedSessionId)) {
      setSelectedSessionId(nextSessions[0]?.id || '');
    }
  }

  async function refreshSessionDetail(sessionId: string) {
    if (!sessionId) {
      setSessionDetail(null);
      setCanUnfreezeBillingLines(false);
      return;
    }
    const res = await getSessionDetail(sessionId);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to load session detail');
      return;
    }
    setSessionDetail(res);
    setCanDelete(Boolean((res as any).can_delete));
    setCanUnfreezeBillingLines(Boolean((res as any).can_unfreeze_billing_lines));
  }

  async function onSelectSessionById() {
    const id = sessionIdLookup.trim();
    if (!id) return;
    const match = sessions.find((s) => s.id === id || s.id.startsWith(id));
    if (match) {
      setSelectedSessionId(match.id);
      setStatusMsg(`Loaded session ${match.id.slice(0, 8)}.`);
      setErrorMsg('');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    setStatusMsg('');
    try {
      const res = await getSessionDetail(id);
      if (!res.success) {
        setErrorMsg(res.message || 'Session id not found');
        return;
      }
      setSelectedSessionId(id);
      setSessionDetail(res);
      setCanDelete(Boolean((res as any).can_delete));
      setCanUnfreezeBillingLines(Boolean((res as any).can_unfreeze_billing_lines));
      setStatusMsg(`Loaded session ${id.slice(0, 8)}.`);
    } finally {
      setLoading(false);
    }
  }

  async function refreshUploadHealth() {
    const res = await getSharepointUploadHealth();
    if (res.success) {
      setUploadHealth({ generated: res.generated, utility: res.utility });
    }
  }

  useEffect(() => {
    const remembered = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (remembered) {
      setSelectedSessionId(remembered);
    }
    void refreshSessions(true);
    void refreshUploadHealth();
    void (async () => {
      try {
        const res = await fetchAssetList(1, 10000, '');
        setAssetOptions(res.data || []);
      } catch (e) {
        setErrorMsg(e instanceof Error ? e.message : 'Failed to load asset list');
      }
    })();
    void (async () => {
      const res = await fetchContractProfileKeys();
      if (res.success && Array.isArray(res.contract_profile_keys)) {
        setRegisteredContractKeys(res.contract_profile_keys);
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedSessionId) return;
    window.localStorage.setItem(SESSION_STORAGE_KEY, selectedSessionId);
  }, [selectedSessionId]);

  useEffect(() => {
    if (!registeredContractKeys.length) return;
    if (!registeredContractKeys.includes(createContractType)) {
      setCreateContractType(registeredContractKeys[0]);
    }
  }, [registeredContractKeys, createContractType]);

  useEffect(() => {
    if (!countryOptions.length) return;
    if (!country || !countryOptions.includes(country)) {
      setCountry(countryOptions[0]);
    }
  }, [countryOptions, country]);

  useEffect(() => {
    if (!country || !createContractType.trim() || !createBillingMonth) {
      setEligibleAssets([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      const res = await fetchEligibleBillingAssets({
        country,
        contract_type: createContractType.trim(),
        billing_month: createBillingMonth,
      });
      if (cancelled) return;
      if (res.success) {
        setEligibleAssets(res.assets || []);
      } else {
        setEligibleAssets([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [country, createContractType, createBillingMonth]);

  useEffect(() => {
    if (!eligibleAssetsFiltered.length) {
      setEligPickAssetCode('');
      return;
    }
    if (!eligPickAssetCode || !eligibleAssetsFiltered.some((a) => a.asset_code === eligPickAssetCode)) {
      setEligPickAssetCode(eligibleAssetsFiltered[0].asset_code);
    }
  }, [eligibleAssetsFiltered, eligPickAssetCode]);

  useEffect(() => {
    if (!portfolioOptions.length) {
      setPortfolio('');
      return;
    }
    if (portfolio && !portfolioOptions.includes(portfolio)) {
      setPortfolio('');
    }
  }, [portfolioOptions, portfolio]);

  useEffect(() => {
    if (eligibleAssets.length > 0) {
      return;
    }
    if (!filteredAssets.length) {
      setAssetCode('');
      setSelectedAssetCodes([]);
      return;
    }
    if (!assetCode || !filteredAssets.some((a) => a.asset_code === assetCode)) {
      setAssetCode(filteredAssets[0].asset_code);
    }
    setSelectedAssetCodes((prev) => prev.filter((c) => filteredAssets.some((a) => a.asset_code === c)));
  }, [filteredAssets, assetCode, eligibleAssets.length]);

  useEffect(() => {
    if (eligibleAssets.length > 0) return;
    if (!assetCode || selectedAssetCodes.includes(assetCode)) return;
    setSelectedAssetCodes((prev) => [...prev, assetCode]);
  }, [assetCode, selectedAssetCodes, eligibleAssets.length]);

  // Removed legacy session asset selection helpers.

  useEffect(() => {
    if (selectedSessionId) {
      void refreshSessionDetail(selectedSessionId);
    } else {
      setSessionDetail(null);
    }
  }, [selectedSessionId]);

  useEffect(() => {
    if (!loading || !selectedSessionId) return;
    const intervalId = window.setInterval(() => {
      void refreshSessionDetail(selectedSessionId);
      void refreshSessions();
      void refreshUploadHealth();
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [loading, selectedSessionId]);

  async function onCreateSession() {
    if (!country) {
      setErrorMsg('Select country.');
      return;
    }
    if (!createBillingMonth) {
      setErrorMsg('Select billing month.');
      return;
    }
    setLoading(true);
    setTaskState('IDLE');
    setErrorMsg('');
    setStatusMsg('');
    const res = await createSession({
      country,
      portfolio: portfolio || undefined,
      billing_month: createBillingMonth,
      billing_contract_type: createContractType.trim() || undefined,
      ...(startDate && endDate ? { start_date: startDate, end_date: endDate } : {}),
    });
    setLoading(false);
    if (!res.success) {
      const existingSessionId = (res as any).existing_session_id as string | undefined;
      if (existingSessionId) {
        setContractTypeFilter(createContractType.trim());
        setBillingMonthFilter(createBillingMonth);
        await refreshSessions(true);
        setErrorMsg(
          `A billing session already exists for this contract and month (${existingSessionId.slice(0, 8)}…). ` +
            'Select it from the session list below — a new session was not created.'
        );
        setStatusMsg('');
        return;
      }
      setErrorMsg(res.message || 'Failed to create session');
      return;
    }
    setStatusMsg(`Session created: ${res.session.id}`);
    await refreshSessions();
    setSelectedSessionId(res.session.id);
  }

  async function onParseInvoices() {
    if (!files || files.length === 0) {
      setErrorMsg('Please select one or more PDF files.');
      return;
    }
    const selected = Array.from(files);
    setUploadRows(selected.map((f) => ({ name: f.name, size: f.size, progress: 0, status: 'uploading' })));
    setLoading(true);
    setTaskState('RUNNING');
    setErrorMsg('');
    setStatusMsg('');
    setSecurityRejections([]);
    const queued = await parseInvoicePdfAsyncWithUploadProgress(
      files,
      selectedSessionId || undefined,
      (loaded, total) => {
        const safeTotal = total > 0 ? total : selected.reduce((s, f) => s + Math.max(0, f.size || 0), 0);
        let remaining = Math.max(0, loaded);
        const next = selected.map((f) => {
          const size = Math.max(1, f.size || 1);
          const used = Math.min(remaining, size);
          remaining = Math.max(0, remaining - size);
          const pct = Math.max(0, Math.min(100, Math.round((used / size) * 100)));
          const prevRow = uploadRows.find((r) => r.name === f.name);
          return {
            name: f.name,
            size: f.size,
            progress: pct,
            status: 'uploading' as const,
            reasonCode: prevRow?.reasonCode,
            reasonMessage: prevRow?.reasonMessage,
          };
        });
        if (safeTotal > 0 && loaded >= safeTotal) {
          for (const row of next) row.progress = 100;
        }
        setUploadRows(next);
      }
    );
    setLoading(false);
    if (!queued.success) {
      setUploadRows((prev) => prev.map((r) => ({ ...r, status: 'failed' })));
      setErrorMsg(queued.message || 'Failed to queue invoice parse');
      return;
    }
    const rejections = ((queued as any).security_rejections || []) as Array<{
      original_filename?: string;
      security_reason_code?: string;
      security_reason_message?: string;
    }>;
    setSecurityRejections(rejections);
    const rejectedEntries: Array<[string, { code: string; message: string }]> = rejections
      .map((r) => [
        String(r.original_filename || '').trim(),
        {
          code: String(r.security_reason_code || ''),
          message: String(r.security_reason_message || ''),
        },
      ] as [string, { code: string; message: string }])
      .filter(([n]) => Boolean(n));
    const rejectedMap = new Map<string, { code: string; message: string }>(rejectedEntries);
    setUploadRows((prev) =>
      prev.map((r) =>
        rejectedMap.has(r.name)
          ? {
              ...r,
              progress: 100,
              status: 'failed',
              reasonCode: rejectedMap.get(r.name)?.code || '',
              reasonMessage: rejectedMap.get(r.name)?.message || '',
            }
          : { ...r, progress: 100, status: 'queued', reasonCode: '', reasonMessage: '' }
      )
    );
    setStatusMsg(`Parse task queued: ${queued.task_id}`);
    setTaskState('RUNNING');
    const filesCount = Number((queued as any).file_count || Array.from(files).length || 0);
    const minEtaSec = Number((queued as any).estimated_seconds_min || 0);
    const maxEtaSec = Number((queued as any).estimated_seconds_max || 0);
    const workers = Number((queued as any).estimated_workers_used || 0);
    const perFileSec = Number((queued as any).estimated_seconds_per_file || 0);
    setStatusMsg(
      `Parse queued in background for ${filesCount} file(s). Estimated ${minEtaSec}-${maxEtaSec}s` +
        (workers > 0 ? ` using ~${workers} worker(s)` : '') +
        (perFileSec > 0 ? ` (~${perFileSec}s per file baseline)` : '') +
        '. ' +
        'Refresh session detail to see per-file statuses.'
    );
    if (Number((queued as any).rejected_file_count || 0) > 0) {
      setStatusMsg(
        `Parse queued. Accepted ${Number((queued as any).accepted_file_count || 0)} / ${filesCount} file(s); ` +
          `${Number((queued as any).rejected_file_count || 0)} rejected by security checks.`
      );
    }
    if (selectedSessionId) {
      await refreshSessionDetail(selectedSessionId);
    }
  }

  async function onGenerateTable() {
    if (!selectedSessionId) {
      setErrorMsg('Select a session first.');
      return;
    }
    setLoading(true);
    setTaskState('RUNNING');
    setErrorMsg('');
    setStatusMsg('');
    const queued = await generateBillingTableAsync(selectedSessionId, defaultExportKwh);
    setLoading(false);
    if (!queued.success) {
      setErrorMsg(queued.message || 'Failed to queue billing table generation');
      return;
    }
    setStatusMsg(`Billing table task queued: ${queued.task_id}`);
    setLoading(true);
    try {
      const result = await waitForTask(queued.task_id, 'Generate Billing Table');
      const rows = Array.isArray((result as any).line_items) ? (result as any).line_items.length : 0;
      const included = Number((result as any).included_assets_count || 0);
      const skipped = Number((result as any).skipped_assets_count || 0);
      const persistNote = formatBillingTableWriteSummary((result as any).billing_table_write);
      if (included || skipped) {
        setStatusMsg(
          `Billing table generated: ${rows} row(s) for ${included} asset(s). ${skipped} asset(s) skipped (pending utility data).${persistNote}`
        );
      } else {
        setStatusMsg(`Billing table generated (${rows} row(s)).${persistNote}`);
      }
    } catch (err) {
      setTaskState('FAILED');
      setErrorMsg(err instanceof Error ? err.message : 'Failed to generate billing table');
    } finally {
      setLoading(false);
    }
    await refreshSessionDetail(selectedSessionId);
    await refreshSessions();
  }

  async function onAddAssetToSession() {
    if (!selectedSessionId) {
      setErrorMsg('Select a session first.');
      return;
    }
    const code = sessionAddAssetCode.trim();
    if (!code) {
      setErrorMsg('Enter an asset code to add.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    setStatusMsg('');
    try {
      const res = await addAssetToBillingSession(selectedSessionId, { asset_code: code });
      if (!res.success) {
        setErrorMsg(res.message || 'Failed to add asset to session');
        return;
      }
      setStatusMsg(`Asset added to session: ${res.added}`);
      setSessionAddAssetCode('');
      await refreshSessionDetail(selectedSessionId);
      await refreshSessions();
    } finally {
      setLoading(false);
    }
  }

  async function onRecalculateLines() {
    if (!selectedSessionId) {
      setErrorMsg('Select a session first.');
      return;
    }
    setLoading(true);
    setTaskState('RUNNING');
    setErrorMsg('');
    setStatusMsg('');
    const queued = await recalculateBillingLinesAsync(selectedSessionId, defaultExportKwh);
    setLoading(false);
    if (!queued.success) {
      setErrorMsg(queued.message || 'Failed to queue recalculate');
      return;
    }
    setStatusMsg(`Recalculate task queued: ${queued.task_id}`);
    setLoading(true);
    try {
      const result = await waitForTask(queued.task_id, 'Recalculate billing lines');
      const n = Array.isArray((result as any).line_items) ? (result as any).line_items.length : 0;
      const persistNote = formatBillingTableWriteSummary((result as any).billing_table_write);
      setStatusMsg(`Billing lines recalculated (${n} row(s)).${persistNote}`);
    } catch (err) {
      setTaskState('FAILED');
      setErrorMsg(err instanceof Error ? err.message : 'Failed to recalculate billing lines');
    } finally {
      setLoading(false);
    }
    await refreshSessionDetail(selectedSessionId);
    await refreshSessions();
  }

  async function onGenerateInvoice() {
    if (!selectedSessionId) {
      setErrorMsg('Select a session first.');
      return;
    }
    setLoading(true);
    setTaskState('RUNNING');
    setErrorMsg('');
    setStatusMsg('');
    const queued = await generateInvoiceAsync(selectedSessionId);
    setLoading(false);
    if (!queued.success) {
      const qm = queued.message || 'Failed to queue invoice generation';
      setErrorMsg(qm);
      await Swal.fire({ icon: 'error', title: 'Could not queue invoice', text: qm });
      return;
    }
    setStatusMsg(`Invoice task queued: ${queued.task_id}`);
    setLoading(true);
    try {
      const result = await waitForTask(queued.task_id, 'Generate Invoice');
      const generated = Array.isArray((result as any).generated_invoices) ? (result as any).generated_invoices : [];
      const failed = Array.isArray((result as any).failed_invoices) ? (result as any).failed_invoices : [];
      const included = Number((result as any).included_assets_count || 0);
      const skipped = Number((result as any).skipped_assets_count || 0);
      let summary: string;
      if (generated.length > 0 && failed.length > 0) {
        summary =
          `Invoice run finished: ${generated.length} generated, ${failed.length} failed` +
          (skipped ? `, ${skipped} skipped (pending utility/lines)` : '') +
          ' (see Billing line items tab).';
      } else if (generated.length > 1) {
        if (included || skipped) {
          summary = `Invoice PDFs generated: ${generated.length} files for ${included} asset(s). ${skipped} asset(s) skipped.`;
        } else {
          summary = `Invoice PDFs generated: ${generated.length} asset-level files.`;
        }
      } else {
        summary = `Invoice PDF generated (version ${String((result.generated_invoice as any)?.version || '')}).`;
      }
      setStatusMsg(summary);
      await Swal.fire({ icon: 'success', title: 'Invoice generation complete', text: summary });
    } catch (err) {
      setTaskState('FAILED');
      const msg = err instanceof Error ? err.message : 'Failed to generate invoice PDF';
      setErrorMsg(msg);
      await Swal.fire({ icon: 'error', title: 'Invoice generation failed', text: msg });
    } finally {
      setLoading(false);
    }
    await refreshSessionDetail(selectedSessionId);
    await refreshSessions();
    await refreshUploadHealth();
  }

  async function onPostInvoice() {
    if (!selectedSessionId) {
      setErrorMsg('Select a session first.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    setStatusMsg('');
    try {
      const res = await postInvoice(selectedSessionId);
      if (!res.success) {
        setErrorMsg(res.message || 'Failed to post invoice');
        return;
      }
      setStatusMsg('Invoice marked as POSTED.');
      await refreshSessionDetail(selectedSessionId);
      await refreshSessions();
    } finally {
      setLoading(false);
    }
  }

  async function onTestSharepointConnection() {
    setLoading(true);
    setErrorMsg('');
    setStatusMsg('');
    setSharepointTestResult('');
    try {
      const res = await testSharepointConnection({
        country: country || 'SG',
        asset_name: selectedAsset?.asset_name || 'ERH_TEST_ASSET',
      });
      if (!res.success) {
        setErrorMsg(res.message || 'SharePoint connectivity test failed.');
        return;
      }
      setStatusMsg(`SharePoint test ok (${res.upload_mode})`);
      setSharepointTestResult(`${res.sharepoint_remote_path}`);
      await refreshUploadHealth();
    } finally {
      setLoading(false);
    }
  }

  async function onCreateUtilityInvoice() {
    if (!selectedSessionId) return;
    setLoading(true);
    setErrorMsg('');
    const res = await createUtilityInvoice(selectedSessionId, {
      invoice_number: newUtilityInvoiceNo,
      total_amount: newUtilityTotalAmount,
      asset_code: selectedAssetCodes[0] || assetCode || '',
      currency_code: 'SGD',
    });
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to create utility invoice');
      return;
    }
    setStatusMsg(`Utility invoice created: ${res.utility_invoice_id}`);
    setNewUtilityInvoiceNo('');
    setNewUtilityTotalAmount('');
    await refreshSessionDetail(selectedSessionId);
  }

  async function onCreatePayment() {
    if (!selectedSessionId || !newPaymentInvoiceId) return;
    setLoading(true);
    setErrorMsg('');
    const res = await createPayment(selectedSessionId, {
      invoice_id: newPaymentInvoiceId,
      payment_paid: newPaymentAmount,
      payment_status: 'pending',
    });
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to create payment');
      return;
    }
    setStatusMsg(`Payment created: ${res.payment_id}`);
    setNewPaymentAmount('');
    await refreshSessionDetail(selectedSessionId);
  }

  async function onCreateMeterReading() {
    if (!selectedSessionId || !newReadingDeviceId || !newReadingValue) return;
    setLoading(true);
    setErrorMsg('');
    const res = await createMeterReading(selectedSessionId, {
      device_id: newReadingDeviceId,
      cumulative_value: newReadingValue,
      source: 'manual',
      data_quality: 'ok',
      reading_role: 'intermediate',
      period_label: `${startDate || ''}_${endDate || ''}`,
    });
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to create meter reading');
      return;
    }
    setStatusMsg(`Meter reading created: ${res.meter_reading_id}`);
    setNewReadingValue('');
    await refreshSessionDetail(selectedSessionId);
  }

  async function onCreateAssetGeneration() {
    if (!selectedSessionId || !newAssetGenMonth) return;
    const assetNumber = selectedAssetCodes[0] || assetCode || '';
    setLoading(true);
    const res = await createAssetGeneration(selectedSessionId, {
      asset_number: assetNumber,
      month: newAssetGenMonth,
      pv_generation_kwh: newAssetGenKwh,
    });
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to create asset generation');
      return;
    }
    setStatusMsg(`Asset generation created: ${res.asset_generation_id}`);
    setNewAssetGenMonth('');
    setNewAssetGenKwh('');
    await refreshSessionDetail(selectedSessionId);
  }

  async function onCreatePenalty() {
    if (!selectedSessionId || !newPenaltyType) return;
    const assetNumber = selectedAssetCodes[0] || assetCode || '';
    setLoading(true);
    const res = await createPenalty(selectedSessionId, {
      asset_number: assetNumber,
      penalty_type: newPenaltyType,
      penalty_charges: newPenaltyAmount,
    });
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to create penalty');
      return;
    }
    setStatusMsg(`Penalty created: ${res.penalty_id}`);
    setNewPenaltyType('');
    setNewPenaltyAmount('');
    await refreshSessionDetail(selectedSessionId);
  }

  async function onCreateAdjustment() {
    if (!selectedSessionId || !newAdjustmentType) return;
    const assetNumber = selectedAssetCodes[0] || assetCode || '';
    setLoading(true);
    const res = await createAdjustment(selectedSessionId, {
      asset_number: assetNumber,
      adjustment_type: newAdjustmentType,
      adjustment_amount: newAdjustmentAmount,
    });
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Failed to create adjustment');
      return;
    }
    setStatusMsg(`Adjustment created: ${res.adjustment_id}`);
    setNewAdjustmentType('');
    setNewAdjustmentAmount('');
    await refreshSessionDetail(selectedSessionId);
  }

  const sessionDataBundle = useMemo((): SessionDetailBundle | null => {
    if (!sessionDetail) return null;
    const d = sessionDetail as Record<string, unknown>;
    return {
      line_items: (d.line_items as SessionDetailBundle['line_items']) || [],
      parsed_invoices: (d.parsed_invoices as SessionDetailBundle['parsed_invoices']) || [],
      upload_summary: (d.upload_summary as SessionDetailBundle['upload_summary']) || [],
      generation_blockers: (d.generation_blockers as SessionDetailBundle['generation_blockers']) || [],
      invoice_generation_allowed:
        typeof d.invoice_generation_allowed === 'boolean' ? d.invoice_generation_allowed : true,
      invoice_generation_blockers:
        (d.invoice_generation_blockers as SessionDetailBundle['invoice_generation_blockers']) || [],
      pending_assets: (d.pending_assets as SessionDetailBundle['pending_assets']) || [],
      generated_invoices: (d.generated_invoices as SessionDetailBundle['generated_invoices']) || [],
      utility_invoices: (d.utility_invoices as SessionDetailBundle['utility_invoices']) || [],
      payments: (d.payments as SessionDetailBundle['payments']) || [],
      meter_readings: (d.meter_readings as SessionDetailBundle['meter_readings']) || [],
      asset_generation: (d.asset_generation as SessionDetailBundle['asset_generation']) || [],
      penalties: (d.penalties as SessionDetailBundle['penalties']) || [],
      adjustments: (d.adjustments as SessionDetailBundle['adjustments']) || [],
      billing_audit_logs: (d.billing_audit_logs as SessionDetailBundle['billing_audit_logs']) || [],
    };
  }, [sessionDetail]);

  const billingLinesFrozen = useMemo(() => {
    const lines = sessionDataBundle?.line_items ?? [];
    return lines.some((li) => {
      const f = li.is_frozen;
      return f === true || f === 1 || f === 'true';
    });
  }, [sessionDataBundle]);

  const generationBlockers = useMemo(
    () => ((sessionDetail as any)?.generation_blockers as Array<Record<string, unknown>> | undefined) || [],
    [sessionDetail]
  );
  const invoiceHardBlockers = useMemo(
    () =>
      ((sessionDetail as any)?.invoice_generation_blockers as Array<Record<string, unknown>> | undefined) || [],
    [sessionDetail]
  );
  const invoiceGenerationAllowed = useMemo(() => {
    const v = (sessionDetail as any)?.invoice_generation_allowed;
    return typeof v === 'boolean' ? v : true;
  }, [sessionDetail]);
  const invoiceGenerationBlocked = !invoiceGenerationAllowed || invoiceHardBlockers.length > 0;
  const pendingAssets = useMemo(
    () => ((sessionDetail as any)?.pending_assets as Array<Record<string, unknown>> | undefined) || [],
    [sessionDetail]
  );
  const conflicts = useMemo(
    () => ((sessionDetail as any)?.conflicts as Array<Record<string, unknown>> | undefined) || [],
    [sessionDetail]
  );
  const coverageSummary = useMemo(
    () => ((sessionDetail as any)?.coverage_summary as Record<string, unknown> | undefined) || {},
    [sessionDetail]
  );
  const localFilesSummary = useMemo(() => {
    const rows = (((sessionDetail as any)?.upload_summary as Array<Record<string, unknown>> | undefined) || []).filter(
      (r) => Boolean(r?.local_file_exists)
    );
    const totalBytes = rows.reduce((sum, r) => {
      const v = Number(r?.local_file_size_bytes ?? 0);
      return sum + (Number.isFinite(v) && v > 0 ? v : 0);
    }, 0);
    return {
      rows,
      count: rows.length,
      totalBytes,
    };
  }, [sessionDetail]);
  const hasLocalFiles = localFilesSummary.count > 0;
  const parseTimingSummary = useMemo(() => {
    const rows = (((sessionDetail as any)?.upload_summary as Array<Record<string, unknown>> | undefined) || []).filter(
      (r) => r?.parse_elapsed_seconds !== null && r?.parse_elapsed_seconds !== undefined && r?.parse_elapsed_seconds !== ''
    );
    const values = rows
      .map((r) => Number(r.parse_elapsed_seconds))
      .filter((n) => Number.isFinite(n) && n >= 0);
    if (!values.length) {
      return { count: 0, avg: 0, min: 0, max: 0 };
    }
    const sum = values.reduce((a, b) => a + b, 0);
    return {
      count: values.length,
      avg: sum / values.length,
      min: Math.min(...values),
      max: Math.max(...values),
    };
  }, [sessionDetail]);
  const conflictIds = useMemo(
    () =>
      conflicts
        .map((c) => String(c.billing_invoice_pdf_id || '').trim())
        .filter(Boolean),
    [conflicts]
  );

  async function handleTabDelete(tab: TabId, row: Record<string, unknown>) {
    if (!selectedSessionId) return;
    if (!window.confirm('Delete this record?')) return;
    const id =
      row.payment_id != null && String(row.payment_id) !== ''
        ? String(row.payment_id)
        : String(row.id ?? '');
    setLoading(true);
    setErrorMsg('');
    let res: { success: boolean; message?: string };
    switch (tab) {
      case 'parsed':
        res = await deleteParsedInvoice(id);
        break;
      case 'lines':
        res = await deleteBillingLineItem(id);
        break;
      case 'utility':
        res = await deleteUtilityInvoice(id);
        break;
      case 'generated':
        res = await deleteGeneratedInvoice(id);
        break;
      case 'payments':
        res = await deletePayment(id);
        break;
      case 'meters':
        res = await deleteMeterReading(id);
        break;
      case 'generation':
        res = await deleteAssetGeneration(id);
        break;
      case 'penalties':
        res = await deletePenalty(id);
        break;
      case 'adjustments':
        res = await deleteAdjustment(id);
        break;
      default:
        setLoading(false);
        return;
    }
    setLoading(false);
    if (!res.success) {
      setErrorMsg(res.message || 'Delete failed');
      return;
    }
    setStatusMsg('Record deleted');
    await refreshSessionDetail(selectedSessionId);
  }

  function formatLineItemPdfFailures(failed: Array<Record<string, unknown>>): string {
    if (!failed.length) return '';
    return failed
      .map((f) => {
        const asset = String(f.asset_code || f.asset_name || '').trim();
        const msg = String(f.message || '').trim();
        const err = String(f.error || '').trim();
        const detail = msg || err || 'Unknown error';
        return asset ? `${asset}: ${detail}` : detail;
      })
      .join('\n');
  }

  async function onGenerateLineItemPdf(row: Record<string, unknown>) {
    if (!selectedSessionId) {
      setErrorMsg('Select a billing session first.');
      await Swal.fire({ icon: 'warning', title: 'Row PDF', text: 'Select a billing session first.' });
      return;
    }
    const rowId = String(row?.id ?? '').trim();
    if (!rowId) {
      setErrorMsg('Missing line item id.');
      await Swal.fire({
        icon: 'error',
        title: 'Row PDF',
        text: 'Missing line item id. Refresh the page and try again.',
      });
      return;
    }
    setLoading(true);
    setTaskState('RUNNING');
    setErrorMsg('');
    setStatusMsg('');
    try {
      const res = await generateLineItemInvoice(rowId);
      setLoading(false);
      if (!res.success) {
        const msg = res.message || 'Failed to generate row PDF';
        setErrorMsg(msg);
        setTaskState('FAILED');
        await Swal.fire({ icon: 'error', title: 'Row PDF failed', text: msg });
        return;
      }

      let payload: Record<string, unknown>;
      if (res.status === 'queued' && res.task_id) {
        setStatusMsg(`Row PDF task queued: ${res.task_id}`);
        setLoading(true);
        try {
          payload = (await waitForTask(res.task_id, 'Row PDF')) as Record<string, unknown>;
        } catch (e) {
          setTaskState('FAILED');
          const msg = e instanceof Error ? e.message : 'Row PDF task failed';
          setErrorMsg(msg);
          await Swal.fire({ icon: 'error', title: 'Row PDF failed', text: msg });
          return;
        } finally {
          setLoading(false);
        }
      } else {
        payload = res as unknown as Record<string, unknown>;
      }
      setTaskState('SUCCESS');

      const generated = Array.isArray(payload.generated_invoices) ? payload.generated_invoices.length : 0;
      const failedRows = Array.isArray(payload.failed_invoices) ? payload.failed_invoices : [];
      const failed = failedRows.length;
      const failureText = formatLineItemPdfFailures(failedRows as Array<Record<string, unknown>>);

      if (failed > 0 && generated === 0) {
        const summary = `Nothing generated (${failed} failure(s)). Common causes: all lines still frozen (unfreeze first), or inconsistent freeze on the same asset.`;
        setStatusMsg(summary);
        setErrorMsg(failureText || summary);
        await Swal.fire({
          icon: 'warning',
          title: 'Row / group PDF — not generated',
          text: failureText ? `${summary}\n\n${failureText}` : summary,
        });
        await refreshSessionDetail(selectedSessionId);
        await refreshSessions();
        await refreshUploadHealth();
        return;
      }

      if (failed > 0 && generated > 0) {
        const okMsg = `Row PDF: ${generated} generated, ${failed} failed (see details).`;
        setStatusMsg(okMsg);
        await Swal.fire({
          icon: 'warning',
          title: 'Row PDF — partial',
          text: `${okMsg}\n\n${failureText}`,
        });
        await refreshSessionDetail(selectedSessionId);
        await refreshSessions();
        await refreshUploadHealth();
        return;
      }

      const okMsg = `Row PDF run finished: ${generated} generated, ${failed} failed.`;
      setStatusMsg(okMsg);
      await Swal.fire({ icon: 'success', title: 'Row PDF', text: okMsg });
      await refreshSessionDetail(selectedSessionId);
      await refreshSessions();
      await refreshUploadHealth();
    } catch (e) {
      console.error('[ERH] generateLineItemInvoice', rowId, e);
      const msg = e instanceof Error ? e.message : 'Network or unexpected error while generating PDF.';
      setErrorMsg(msg);
      setTaskState('FAILED');
      await Swal.fire({ icon: 'error', title: 'Row PDF failed', text: msg });
    } finally {
      setLoading(false);
    }
  }

  async function onUtilityUnfreeze(row: Record<string, unknown>) {
    const rowId = String(row.id || '');
    if (!rowId || !selectedSessionId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await updateUtilityInvoice(rowId, { action: 'unfreeze' });
      if (!res.success) {
        setErrorMsg(res.message || 'Failed to unfreeze utility row');
        return;
      }
      setStatusMsg('Utility row unfrozen. Edit and save to freeze again.');
      await refreshSessionDetail(selectedSessionId);
    } finally {
      setLoading(false);
    }
  }

  async function onUtilitySave(row: Record<string, unknown>, payload: Record<string, unknown>) {
    const rowId = String(row.id || '');
    if (!rowId || !selectedSessionId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const incomingAction = String((payload as any)?.action || '').trim();
      const action =
        incomingAction === 'relink' || incomingAction === 'mark_failed' ? incomingAction : 'save_and_freeze';
      const res = await updateUtilityInvoice(rowId, { ...payload, action });
      if (!res.success) {
        setErrorMsg(res.message || 'Failed to save utility row');
        return;
      }
      if (action === 'relink') setStatusMsg('Utility row relinked. You can now fill missing fields and save.');
      else if (action === 'mark_failed') setStatusMsg('Utility row marked as failed.');
      else setStatusMsg('Utility row saved and frozen.');
      await refreshSessionDetail(selectedSessionId);
    } finally {
      setLoading(false);
    }
  }

  async function onFreezeAllUtilityRows() {
    if (!selectedSessionId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await freezeAllUtilityInvoices(selectedSessionId);
      if (!res.success) {
        setErrorMsg(res.message || 'Failed to freeze utility rows');
        return;
      }
      setStatusMsg(`Frozen ${String(res.frozen_rows)} utility row(s).`);
      await refreshSessionDetail(selectedSessionId);
    } finally {
      setLoading(false);
    }
  }

  async function onUtilityPass(row: Record<string, unknown>) {
    const rowId = String(row.id || '');
    if (!rowId || !selectedSessionId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await passUtilityInvoice(rowId);
      if (!res.success) {
        setErrorMsg(res.message || 'Failed to Pass utility row');
        return;
      }
      setStatusMsg('Utility row Passed for billing.');
      await refreshSessionDetail(selectedSessionId);
    } finally {
      setLoading(false);
    }
  }

  async function onUnfreezeBillingLines() {
    if (!selectedSessionId) return;
    if (!window.confirm('Unfreeze all billing lines so the table can be recalculated?')) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await unfreezeBillingLines(selectedSessionId);
      if (!res.success) {
        setErrorMsg(res.message || 'Unfreeze failed');
        return;
      }
      setStatusMsg('Billing lines unfrozen');
      await refreshSessionDetail(selectedSessionId);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Unfreeze failed');
    } finally {
      setLoading(false);
    }
  }

  async function onUnfreezeBillingLineRow(row: Record<string, unknown>) {
    if (!selectedSessionId) return;
    const lineId = String(row.id ?? '');
    if (!lineId) return;
    if (!window.confirm('Unfreeze this billing line so it can be deleted or recalculated?')) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await unfreezeBillingLines(selectedSessionId, { lineItemId: lineId });
      if (!res.success) {
        setErrorMsg(res.message || 'Unfreeze failed');
        return;
      }
      setStatusMsg('Billing line unfrozen');
      await refreshSessionDetail(selectedSessionId);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Unfreeze failed');
    } finally {
      setLoading(false);
    }
  }

  async function onUnfreezeBillingLineGroup(groupKey: string) {
    if (!selectedSessionId || !sessionDetail) return;
    const items = (sessionDetail.line_items || []) as Array<Record<string, unknown>>;
    const targets = items.filter(
      (r) =>
        lineGroupKeyForErhLineRow(r) === groupKey &&
        (r.is_frozen === true || r.is_frozen === 1 || r.is_frozen === 'true'),
    );
    if (!targets.length) {
      setStatusMsg('No frozen lines in this group.');
      return;
    }
    if (!window.confirm(`Unfreeze ${targets.length} billing line(s) in this asset + utility PDF group?`)) return;
    setLoading(true);
    setErrorMsg('');
    try {
      for (const row of targets) {
        const res = await unfreezeBillingLines(selectedSessionId, { lineItemId: String(row.id) });
        if (!res.success) {
          setErrorMsg(res.message || 'Unfreeze failed');
          return;
        }
      }
      setStatusMsg('Billing lines in group unfrozen');
      await refreshSessionDetail(selectedSessionId);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Unfreeze failed');
    } finally {
      setLoading(false);
    }
  }

  async function downloadGeneratedInvoices(ids: string[]) {
    if (!ids.length) return;
    setLoading(true);
    setErrorMsg('');
    setStatusMsg('');
    let okCount = 0;
    let failCount = 0;
    try {
      let useZip = true;
      let zip: any = null;
      try {
        zip = new JSZip();
      } catch {
        useZip = false;
      }
      setGeneratedDownloadProgress({
        active: true,
        total: ids.length,
        completed: 0,
        ok: 0,
        failed: 0,
        mode: useZip ? 'zip' : 'files',
      });
      for (const id of ids) {
        try {
          const res = await fetch(`/energy-revenue-hub/api/generated-invoices/${id}/download/`, {
            credentials: 'same-origin',
          });
          if (!res.ok) {
            failCount += 1;
            continue;
          }
          const blob = await res.blob();
          const disp = res.headers.get('content-disposition') || '';
          const match = /filename="?([^"]+)"?/i.exec(disp);
          const fileName = (match?.[1] || `generated-invoice-${id}.pdf`).trim();
          if (useZip && zip) {
            zip.file(fileName, blob);
          } else {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
          }
          okCount += 1;
          setGeneratedDownloadProgress((prev) => ({
            ...prev,
            completed: prev.completed + 1,
            ok: okCount,
            failed: failCount,
          }));
        } catch {
          failCount += 1;
          setGeneratedDownloadProgress((prev) => ({
            ...prev,
            completed: prev.completed + 1,
            ok: okCount,
            failed: failCount,
          }));
        }
      }
      if (useZip && zip && okCount > 0) {
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        const zipUrl = window.URL.createObjectURL(zipBlob);
        const a = document.createElement('a');
        const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        a.href = zipUrl;
        a.download = `generated-invoices-${stamp}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(zipUrl);
      }
      if (failCount > 0) {
        setStatusMsg(
          useZip
            ? `ZIP download prepared with ${okCount} file(s), ${failCount} failed.`
            : `Downloaded ${okCount} file(s), ${failCount} failed.`
        );
      } else {
        setStatusMsg(useZip ? `ZIP downloaded with ${okCount} generated invoice file(s).` : `Downloaded ${okCount} generated invoice file(s).`);
      }
    } finally {
      setLoading(false);
      setGeneratedDownloadProgress((prev) => ({ ...prev, active: false }));
    }
  }

  async function onResolveConflict(billingInvoicePdfId: string, action: 'apply' | 'reject') {
    if (!billingInvoicePdfId || !selectedSessionId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await resolveBillingInvoicePdfMerge(billingInvoicePdfId, action);
      if (!res.success) {
        setErrorMsg(res.message || `Failed to ${action} conflict`);
        return;
      }
      setStatusMsg(`Conflict ${action}ed.`);
      await refreshSessionDetail(selectedSessionId);
      await refreshSessions();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="container py-4 page-container"
      style={{
        background: bgGradient,
        color: textPrimary,
        minHeight: '100vh',
      }}
    >
      <div className="d-flex justify-content-between align-items-center mb-3 section-card">
        <h1 className="mb-0 page-title">Energy Revenue Hub</h1>
        <div className="d-flex align-items-center gap-2">
          <span
            className={`status-badge ${
              taskState === 'RUNNING'
                ? 'status-in-progress'
                : taskState === 'SUCCESS'
                  ? 'status-active'
                  : taskState === 'FAILED'
                    ? 'priority-critical'
                    : 'status-inactive'
            }`}
          >
            {taskState}
          </span>
          <button className="btn-secondary btn-sm" onClick={() => window.location.assign('/')}>
          Return to Dashboard
          </button>
        </div>
      </div>
      <div
        className="mb-3"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 50,
          background: theme === 'dark' ? 'rgba(15, 23, 42, 0.92)' : 'rgba(248, 250, 252, 0.94)',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
          paddingTop: 8,
          paddingBottom: 8,
          marginTop: -8,
          marginLeft: -12,
          marginRight: -12,
          paddingLeft: 12,
          paddingRight: 12,
          borderBottom: '1px solid rgba(148,163,184,0.28)',
        }}
      >
        {uploadHealth && (
          <div className="hint-text mb-2">
            SharePoint Uploads | Utility: {uploadHealth.utility.uploaded} ok / {uploadHealth.utility.failed} failed | Generated:{' '}
            {uploadHealth.generated.on_sharepoint} ok / {uploadHealth.generated.failed} failed / {uploadHealth.generated.total} total
          </div>
        )}
        {statusMsg && <div className="alert alert-success py-2 mb-2">{statusMsg}</div>}
        {errorMsg && <div className="alert alert-danger py-2 mb-2">{errorMsg}</div>}
        {securityRejections.length > 0 && (
          <div className="alert alert-warning py-2 mb-0">
            <div className="fw-semibold">Security rejections</div>
            {securityRejections.map((r, i) => (
              <div key={`${r.original_filename || 'file'}-${i}`} style={{ fontSize: '0.85rem' }}>
                {String(r.original_filename || 'file')} - {String(r.security_reason_code || 'SECURITY_REJECTED')} -{' '}
                {String(r.security_reason_message || 'Blocked by security validation')}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="section-card mb-3 py-2 px-2">
        <div className="d-flex flex-wrap gap-2" role="tablist">
          {(
            [
              { id: 'session' as const, label: 'Session' },
              { id: 'parse' as const, label: 'Parse' },
              { id: 'billing' as const, label: 'Billing' },
              { id: 'invoice' as const, label: 'Invoice' },
              { id: 'audit' as const, label: 'Audit logs' },
            ] as const
          ).map(({ id, label }) => {
            const disabled = id !== 'session' && !selectedSessionId;
            const active = pageTab === id;
            return (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={active}
                disabled={disabled}
                className="btn btn-sm"
                onClick={() => setPageTab(id)}
                style={{
                  borderRadius: 8,
                  border: active ? '1px solid rgba(59,130,246,0.65)' : '1px solid rgba(148,163,184,0.35)',
                  background: active ? 'rgba(59,130,246,0.18)' : 'transparent',
                  color: textPrimary,
                  fontWeight: active ? 600 : 400,
                  opacity: disabled ? 0.45 : 1,
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
        {selectedSession && (
          <div className="hint-text mt-2 mb-0">
            Active session: <strong>{selectedSession.session_label || selectedSession.id.slice(0, 8)}</strong> ·{' '}
            {selectedSession.billing_contract_type || '—'} · {selectedSession.billing_month || '—'} · {selectedSession.status}
          </div>
        )}
      </div>

      <div className="row g-3">
        {pageTab === 'session' && (
          <ErhSessionTab
            country={country}
            setCountry={setCountry}
            countryOptions={countryOptions}
            createContractType={createContractType}
            setCreateContractType={setCreateContractType}
            registeredContractKeys={registeredContractKeys}
            createBillingMonth={createBillingMonth}
            setCreateBillingMonth={setCreateBillingMonth}
            portfolio={portfolio}
            setPortfolio={setPortfolio}
            portfolioOptions={portfolioOptions}
            assetSearch={assetSearch}
            setAssetSearch={setAssetSearch}
            eligibleAssetsFiltered={eligibleAssetsFiltered}
            startDate={startDate}
            setStartDate={setStartDate}
            endDate={endDate}
            setEndDate={setEndDate}
            onCreateSession={onCreateSession}
            loading={loading}
            contractTypeFilter={contractTypeFilter}
            setContractTypeFilter={setContractTypeFilter}
            billingMonthFilter={billingMonthFilter}
            setBillingMonthFilter={setBillingMonthFilter}
            refreshSessions={refreshSessions}
            sessionSearch={sessionSearch}
            setSessionSearch={setSessionSearch}
            filteredSessions={filteredSessions}
            sessionsLength={sessions.length}
            selectedSessionId={selectedSessionId}
            setSelectedSessionId={setSelectedSessionId}
            sessionIdLookup={sessionIdLookup}
            setSessionIdLookup={setSessionIdLookup}
            onSelectSessionById={onSelectSessionById}
          />
        )}

        {pageTab !== 'session' && (
          <ErhWorkspace
            pageTab={pageTab}
            textMuted={textMuted}
            selectedSessionId={selectedSessionId}
            selectedSession={selectedSession}
            sessionDetail={sessionDetail}
          >
            {pageTab === 'parse' && (
              <ErhParsePanel
                textPrimary={textPrimary}
                textMuted={textMuted}
                loading={loading}
                selectedSessionId={selectedSessionId}
                hasLocalFiles={hasLocalFiles}
                localFilesSummary={localFilesSummary}
                formatBytes={formatBytes}
                coverageSummary={coverageSummary}
                pendingAssets={pendingAssets}
                conflicts={conflicts}
                conflictIds={conflictIds}
                expandedConflictIds={expandedConflictIds}
                setExpandedConflictIds={setExpandedConflictIds}
                parseTimingSummary={parseTimingSummary}
                refreshSessionDetail={refreshSessionDetail}
                onResolveConflict={onResolveConflict}
                canDelete={canDelete}
                setFiles={setFiles}
                uploadRows={uploadRows}
                setUploadRows={setUploadRows}
                onParseInvoices={onParseInvoices}
                sessionDataBundle={sessionDataBundle}
                canUnfreezeBillingLines={canUnfreezeBillingLines}
                billingLinesFrozen={billingLinesFrozen}
                handleTabDelete={handleTabDelete}
                onGenerateLineItemPdf={onGenerateLineItemPdf}
                onUtilityUnfreeze={onUtilityUnfreeze}
                onUtilitySave={onUtilitySave}
                onUtilityPass={onUtilityPass}
                onFreezeAllUtilityRows={onFreezeAllUtilityRows}
                onUnfreezeBillingLineRow={onUnfreezeBillingLineRow}
              />
            )}
            {pageTab === 'billing' && sessionDataBundle && (
              <ErhBillingPanel
                textPrimary={textPrimary}
                textMuted={textMuted}
                loading={loading}
                selectedSessionId={selectedSessionId}
                sessionDataBundle={sessionDataBundle}
                coverageSummary={coverageSummary}
                pendingAssets={pendingAssets}
                conflicts={conflicts}
                onGenerateTable={onGenerateTable}
                onRecalculateLines={onRecalculateLines}
                canUnfreezeBillingLines={canUnfreezeBillingLines}
                onUnfreezeBillingLines={onUnfreezeBillingLines}
                onTestSharepointConnection={onTestSharepointConnection}
                sharepointTestResult={sharepointTestResult}
                canDelete={canDelete}
                sessionAddAssetCode={sessionAddAssetCode}
                setSessionAddAssetCode={setSessionAddAssetCode}
                onAddAssetToSession={onAddAssetToSession}
                billingLinesFrozen={billingLinesFrozen}
                handleTabDelete={handleTabDelete}
                onGenerateLineItemPdf={onGenerateLineItemPdf}
                onUtilityUnfreeze={onUtilityUnfreeze}
                onUtilitySave={onUtilitySave}
                onUtilityPass={onUtilityPass}
                onFreezeAllUtilityRows={onFreezeAllUtilityRows}
                onUnfreezeBillingLineRow={onUnfreezeBillingLineRow}
                onUnfreezeBillingLineGroup={canUnfreezeBillingLines ? onUnfreezeBillingLineGroup : undefined}
                refreshSessionDetail={refreshSessionDetail}
                sessionDetail={sessionDetail}
                newUtilityInvoiceNo={newUtilityInvoiceNo}
                setNewUtilityInvoiceNo={setNewUtilityInvoiceNo}
                newUtilityTotalAmount={newUtilityTotalAmount}
                setNewUtilityTotalAmount={setNewUtilityTotalAmount}
                newPaymentInvoiceId={newPaymentInvoiceId}
                setNewPaymentInvoiceId={setNewPaymentInvoiceId}
                newPaymentAmount={newPaymentAmount}
                setNewPaymentAmount={setNewPaymentAmount}
                newReadingDeviceId={newReadingDeviceId}
                setNewReadingDeviceId={setNewReadingDeviceId}
                newReadingValue={newReadingValue}
                setNewReadingValue={setNewReadingValue}
                newAssetGenMonth={newAssetGenMonth}
                setNewAssetGenMonth={setNewAssetGenMonth}
                newAssetGenKwh={newAssetGenKwh}
                setNewAssetGenKwh={setNewAssetGenKwh}
                newPenaltyType={newPenaltyType}
                setNewPenaltyType={setNewPenaltyType}
                newPenaltyAmount={newPenaltyAmount}
                setNewPenaltyAmount={setNewPenaltyAmount}
                newAdjustmentType={newAdjustmentType}
                setNewAdjustmentType={setNewAdjustmentType}
                newAdjustmentAmount={newAdjustmentAmount}
                setNewAdjustmentAmount={setNewAdjustmentAmount}
                onCreateUtilityInvoice={onCreateUtilityInvoice}
                onCreatePayment={onCreatePayment}
                onCreateMeterReading={onCreateMeterReading}
                onCreateAssetGeneration={onCreateAssetGeneration}
                onCreatePenalty={onCreatePenalty}
                onCreateAdjustment={onCreateAdjustment}
              />
            )}
            {pageTab === 'invoice' && sessionDataBundle && selectedSession && (
              <ErhInvoicePanel
                textPrimary={textPrimary}
                textMuted={textMuted}
                loading={loading}
                selectedSession={selectedSession}
                sessionDetail={sessionDetail}
                sessionDataBundle={sessionDataBundle}
                invoiceGenerationBlocked={invoiceGenerationBlocked}
                invoiceHardBlockers={invoiceHardBlockers}
                generationBlockers={generationBlockers}
                selectedGeneratedIds={selectedGeneratedIds}
                setSelectedGeneratedIds={setSelectedGeneratedIds}
                generatedDownloadProgress={generatedDownloadProgress}
                downloadGeneratedInvoices={downloadGeneratedInvoices}
                onGenerateInvoice={onGenerateInvoice}
                onPostInvoice={onPostInvoice}
                canDelete={canDelete}
                billingLinesFrozen={billingLinesFrozen}
                handleTabDelete={handleTabDelete}
                onGenerateLineItemPdf={onGenerateLineItemPdf}
                onUtilityUnfreeze={onUtilityUnfreeze}
                onUtilitySave={onUtilitySave}
                onUtilityPass={onUtilityPass}
                onFreezeAllUtilityRows={onFreezeAllUtilityRows}
                canUnfreezeBillingLines={canUnfreezeBillingLines}
                onUnfreezeBillingLineRow={onUnfreezeBillingLineRow}
              />
            )}
            {pageTab === 'audit' && sessionDataBundle && (
              <ErhAuditPanel
                sessionDataBundle={sessionDataBundle}
                textPrimary={textPrimary}
                textMuted={textMuted}
                canDelete={canDelete}
                loading={loading}
                handleTabDelete={handleTabDelete}
                onGenerateLineItemPdf={onGenerateLineItemPdf}
                onUtilityUnfreeze={onUtilityUnfreeze}
                onUtilitySave={onUtilitySave}
                onUtilityPass={onUtilityPass}
                onFreezeAllUtilityRows={onFreezeAllUtilityRows}
                billingLinesFrozen={billingLinesFrozen}
                canUnfreezeBillingLines={canUnfreezeBillingLines}
                onUnfreezeBillingLineRow={onUnfreezeBillingLineRow}
              />
            )}
          </ErhWorkspace>
        )}
      </div>
    </div>
  );
}
