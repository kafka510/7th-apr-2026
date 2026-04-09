import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { fetchUtilityInvoiceDetail } from './api';
import { billingSessionIdForFilename, rowsToCsv, triggerCsvDownload } from './erhCsvExport';

const DEFAULT_PAGE_SIZE = 50;

type Row = Record<string, unknown>;

function orderKeys(row: Row, preferred: string[]): string[] {
  const keys = Object.keys(row);
  const rest = keys.filter((k) => !preferred.includes(k)).sort();
  return [...preferred.filter((k) => k in row), ...rest];
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'object') {
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  }
  return String(v);
}

/** Wider max width for short labels; tight for UUIDs and long numeric strings in utility grid */
function utilityColumnMaxWidthPx(colKey: string): number {
  if (colKey === 'id' || colKey === 'billing_session_id' || colKey === 'billing_invoice_pdf_id') return 108;
  if (
    colKey === 'calculated_unit_rate' ||
    colKey === 'net_unit_rate' ||
    colKey === 'anomaly_flag' ||
    colKey === 'unit_rate'
  ) {
    return 132;
  }
  if (colKey === 'parse_review_status') return 100;
  if (colKey === 'is_frozen') return 72;
  return 168;
}

function utilityCellInner(
  colKey: string,
  raw: unknown,
  opts: { textMuted: string; textPrimary: string },
): ReactNode {
  const empty = raw === null || raw === undefined || raw === '';
  if (empty) return <span style={{ color: opts.textMuted }}>—</span>;
  if (colKey === 'parse_review_status') {
    const s = String(raw).toLowerCase();
    const bg =
      s === 'passed'
        ? 'rgba(34, 197, 94, 0.18)'
        : s === 'pending' || s === ''
          ? 'rgba(234, 179, 8, 0.2)'
          : 'rgba(148, 163, 184, 0.2)';
    const fg =
      s === 'passed' ? 'rgb(34, 197, 94)' : s === 'pending' || s === '' ? 'rgb(234, 179, 8)' : opts.textPrimary;
    return (
      <span
        className="text-uppercase"
        style={{
          fontSize: '0.72rem',
          fontWeight: 700,
          letterSpacing: '0.04em',
          padding: '2px 8px',
          borderRadius: 6,
          background: bg,
          color: fg,
        }}
      >
        {String(raw) || 'pending'}
      </span>
    );
  }
  if (colKey === 'is_frozen') {
    const frozen = raw === true || raw === 1 || raw === 'true';
    return (
      <span
        style={{
          fontSize: '0.72rem',
          fontWeight: 700,
          padding: '2px 8px',
          borderRadius: 6,
          background: frozen ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.15)',
          color: frozen ? 'rgb(96, 165, 250)' : opts.textMuted,
        }}
      >
        {frozen ? 'Frozen' : 'No'}
      </span>
    );
  }
  if (
    colKey === 'parse_review_passed_at' ||
    colKey === 'created_at' ||
    colKey === 'updated_at' ||
    colKey === 'frozen_at'
  ) {
    const localTs = formatTimestampLocal(raw);
    if (localTs) {
      return (
        <span title={formatCell(raw)} style={{ fontSize: '0.82rem' }}>
          {localTs}
        </span>
      );
    }
  }
  const full = formatCell(raw);
  const maxW = utilityColumnMaxWidthPx(colKey);
  return (
    <span
      title={full.length > 40 ? full : undefined}
      style={{
        display: 'inline-block',
        maxWidth: maxW,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        verticalAlign: 'top',
      }}
    >
      {full}
    </span>
  );
}

function primaryRowId(row: Row): string | null {
  if (row.payment_id != null && String(row.payment_id) !== '') return String(row.payment_id);
  if (row.id != null && String(row.id) !== '') return String(row.id);
  return null;
}

function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function isBillingLineRowFrozen(row: Row): boolean {
  const f = row.is_frozen;
  return f === true || f === 1 || f === 'true';
}

/** Stable key for asset + utility PDF grouping (matches session detail API). */
export function lineGroupKeyForErhLineRow(r: Row): string {
  const gk = String(r.line_group_key ?? '').trim();
  if (gk) return gk;
  const ac = String(r.asset_code || r.asset_name || '').trim() || 'asset';
  const pdf = String(r.utility_billing_invoice_pdf_id ?? '').trim();
  return `${ac}|${pdf || 'none'}`;
}

function sortBillingLineRowsByGroup(rows: Row[]): Row[] {
  return [...rows].sort((a, b) => {
    const ga = lineGroupKeyForErhLineRow(a);
    const gb = lineGroupKeyForErhLineRow(b);
    if (ga !== gb) return ga.localeCompare(gb);
    const aIssue =
      String(a.invoice_generation_status || '').toLowerCase() === 'failed' ||
      Boolean(String(a.billing_cycle_warning || '').trim());
    const bIssue =
      String(b.invoice_generation_status || '').toLowerCase() === 'failed' ||
      Boolean(String(b.billing_cycle_warning || '').trim());
    const aIssueN = aIssue ? 0 : 1;
    const bIssueN = bIssue ? 0 : 1;
    if (aIssueN !== bIssueN) return aIssueN - bIssueN;
    const aFrozen = String(a.is_frozen ?? 'false').toLowerCase() === 'true' ? 1 : 0;
    const bFrozen = String(b.is_frozen ?? 'false').toLowerCase() === 'true' ? 1 : 0;
    if (aFrozen !== bFrozen) return aFrozen - bFrozen;
    const so = (asNumber(a.sort_order) ?? 0) - (asNumber(b.sort_order) ?? 0);
    if (so !== 0) return so;
    const seg = (asNumber(a.segment_index) ?? 0) - (asNumber(b.segment_index) ?? 0);
    if (seg !== 0) return seg;
    const aTime = String(a.updated_at || a.created_at || a.timestamp || '');
    const bTime = String(b.updated_at || b.created_at || b.timestamp || '');
    return bTime.localeCompare(aTime);
  });
}

function formatTimestampLocal(raw: unknown): string | null {
  if (raw === null || raw === undefined || raw === '') return null;
  const s = String(raw).trim();
  if (!s) return null;
  const t = Date.parse(s);
  if (!Number.isFinite(t)) return null;
  return new Date(t).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'medium' });
}

function ErhDataTable({
  rows,
  preferredKeys,
  emptyMessage,
  textPrimary,
  textMuted,
  showActions,
  loading,
  onDeleteRow,
  extraRowActionLabel,
  onExtraRowAction,
  isExtraRowActionDisabled,
  extraRowButtons,
  isRowDeleteDisabled,
  timestampColumnKeys,
  lineGroupKey,
  renderGroupHeaderRow,
}: {
  rows: Row[];
  preferredKeys: string[];
  emptyMessage: string;
  textPrimary: string;
  textMuted: string;
  showActions?: boolean;
  loading?: boolean;
  onDeleteRow?: (row: Row) => void;
  extraRowActionLabel?: string;
  onExtraRowAction?: (row: Row) => void;
  isExtraRowActionDisabled?: (row: Row) => boolean;
  /** Extra action buttons (e.g. per-row Unfreeze on billing lines). */
  extraRowButtons?: Array<{
    label: string;
    onClick: (row: Row) => void;
    visible?: (row: Row) => boolean;
    disabled?: (row: Row) => boolean;
  }>;
  /** When set, Delete is disabled for rows where this returns true (e.g. frozen line items). */
  isRowDeleteDisabled?: (row: Row) => boolean;
  /** ISO-like timestamp strings shown in the browser's local timezone. */
  timestampColumnKeys?: string[];
  /** Billing lines: group rows visually; key should match backend `line_group_key`. */
  lineGroupKey?: (row: Row) => string | null;
  /** Optional strip above each group (e.g. asset + PDF label and group actions). */
  renderGroupHeaderRow?: (ctx: { groupKey: string; groupOrdinal: number; firstRow: Row }) => ReactNode;
}) {
  const keys = useMemo(() => {
    if (!rows.length) return [] as string[];
    const k = orderKeys(rows[0] as Row, preferredKeys);
    // If the first row has no overlapping keys (sparse API payload), still show expected columns.
    if (k.length > 0) return k;
    return preferredKeys.filter(Boolean);
  }, [rows, preferredKeys]);

  const actionsColSpan = keys.length + (showActions ? 1 : 0);

  const groupOrdinals = useMemo(() => {
    if (!lineGroupKey || !rows.length) return rows.map(() => 0);
    let ord = -1;
    let prev = '';
    const out: number[] = [];
    for (let i = 0; i < rows.length; i++) {
      const gk = (lineGroupKey(rows[i]) ?? '').trim();
      if (i === 0 || gk !== prev) ord += 1;
      out.push(ord);
      prev = gk;
    }
    return out;
  }, [rows, lineGroupKey]);

  if (!rows.length) {
    return (
      <p className="mb-0" style={{ color: textMuted }}>
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="erh-table-wrap" style={{ overflowX: 'auto', maxWidth: '100%' }}>
      <table
        className="table table-sm align-middle mb-0"
        style={{
          color: textPrimary,
          borderCollapse: 'collapse',
          minWidth: 560,
          fontSize: '0.85rem',
        }}
      >
        <thead>
          <tr style={{ borderBottom: '1px solid rgba(148,163,184,0.35)' }}>
            {keys.map((k) => (
              <th key={k} className="text-nowrap px-2 py-2" style={{ fontWeight: 600 }}>
                {k.replace(/_/g, ' ')}
              </th>
            ))}
            {showActions && (
              <th className="text-nowrap px-2 py-2" style={{ fontWeight: 600 }}>
                Actions
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const gk = (lineGroupKey?.(row) ?? '').trim();
            const prevGk = i > 0 ? (lineGroupKey?.(rows[i - 1]) ?? '').trim() : '';
            const isNewGroup = Boolean(lineGroupKey) && (i === 0 || gk !== prevGk);
            const ord = groupOrdinals[i] ?? 0;
            const banded =
              lineGroupKey &&
              (ord % 2 === 0 ? 'rgba(59, 130, 246, 0.05)' : 'rgba(148, 163, 184, 0.04)');
            return (
              <Fragment key={`${primaryRowId(row) ?? 'row'}::${i}`}>
                {isNewGroup && renderGroupHeaderRow && (
                  <tr>
                    <td
                      colSpan={actionsColSpan}
                      className="p-0"
                      style={{ borderBottom: 'none', verticalAlign: 'middle' }}
                    >
                      {renderGroupHeaderRow({ groupKey: gk, groupOrdinal: ord, firstRow: row })}
                    </td>
                  </tr>
                )}
                <tr
                  style={{
                    borderBottom: '1px solid rgba(148,163,184,0.2)',
                    background: banded || undefined,
                    boxShadow: lineGroupKey ? 'inset 3px 0 0 rgba(59,130,246,0.35)' : undefined,
                  }}
                >
                  {keys.map((k) => {
                    const raw = (row as Row)[k];
                    if (
                      (k === 'download' || k === 'latest_generated_invoice_download' || k === 'download_original') &&
                      typeof raw === 'string' &&
                      raw.startsWith('/')
                    ) {
                      return (
                        <td key={k} className="px-2 py-1 align-top">
                          <a href={raw} target="_blank" rel="noopener noreferrer">
                            Download PDF
                          </a>
                        </td>
                      );
                    }
                    const isLong = typeof raw === 'object' && raw !== null;
                    const localTs =
                      !isLong && timestampColumnKeys?.includes(k) ? formatTimestampLocal(raw) : null;
                    return (
                      <td key={k} className="px-2 py-1 align-top">
                        {isLong ? (
                          <pre
                            className="mb-0 small"
                            style={{
                              color: textMuted,
                              maxWidth: 360,
                              maxHeight: 160,
                              overflow: 'auto',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                            }}
                          >
                            {formatCell(raw)}
                          </pre>
                        ) : localTs ? (
                          <span title={formatCell(raw)}>{localTs}</span>
                        ) : (
                          <span>{raw === null || raw === undefined ? '—' : formatCell(raw)}</span>
                        )}
                      </td>
                    );
                  })}
                  {showActions && (onDeleteRow || onExtraRowAction || (extraRowButtons && extraRowButtons.length)) && (
                    <td className="px-2 py-1 align-top text-nowrap">
                      {extraRowButtons?.map((btn, bi) => {
                        if (btn.visible && !btn.visible(row)) return null;
                        return (
                          <button
                            key={`${btn.label}-${bi}`}
                            type="button"
                            className="btn btn-sm btn-warning text-dark fw-semibold me-1"
                            style={{ boxShadow: '0 1px 3px rgba(217, 119, 6, 0.4)' }}
                            disabled={loading || Boolean(btn.disabled?.(row))}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              btn.onClick(row);
                            }}
                          >
                            {btn.label}
                          </button>
                        );
                      })}
                      {onExtraRowAction && (
                        <button
                          type="button"
                          className="btn btn-sm btn-primary fw-semibold me-1"
                          style={{ boxShadow: '0 1px 3px rgba(37, 99, 235, 0.45)' }}
                          disabled={loading || Boolean(isExtraRowActionDisabled?.(row))}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onExtraRowAction(row);
                          }}
                        >
                          {extraRowActionLabel || 'Run'}
                        </button>
                      )}
                      {onDeleteRow && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger fw-semibold"
                          style={{ borderWidth: 2 }}
                          disabled={loading || !primaryRowId(row) || Boolean(isRowDeleteDisabled?.(row))}
                          onClick={() => onDeleteRow(row)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export type SessionDetailBundle = {
  line_items: Row[];
  parsed_invoices: Row[];
  upload_summary?: Row[];
  generation_blockers?: Row[];
  invoice_generation_allowed?: boolean;
  invoice_generation_blockers?: Row[];
  pending_assets?: Row[];
  generated_invoices: Row[];
  utility_invoices: Row[];
  payments: Row[];
  meter_readings: Row[];
  asset_generation: Row[];
  penalties: Row[];
  adjustments: Row[];
  billing_audit_logs: Row[];
};

export type TabId =
  | 'parsed'
  | 'lines'
  | 'utility'
  | 'generated'
  | 'payments'
  | 'meters'
  | 'generation'
  | 'penalties'
  | 'adjustments'
  | 'audit';

const TABS: { id: TabId; label: string }[] = [
  { id: 'parsed', label: 'Parsed invoices' },
  { id: 'lines', label: 'Billing line items' },
  { id: 'utility', label: 'Utility invoices' },
  { id: 'generated', label: 'Generated invoices' },
  { id: 'payments', label: 'Payments' },
  { id: 'meters', label: 'Meter readings' },
  { id: 'generation', label: 'Asset generation' },
  { id: 'penalties', label: 'Penalties' },
  { id: 'adjustments', label: 'Adjustments' },
  { id: 'audit', label: 'Audit log' },
];

function parseStartedAtMs(r: Row): number {
  const s = String(r.parse_started_at ?? '').trim();
  if (!s) return 0;
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : 0;
}

export function SessionDataTabs({
  bundle,
  textPrimary,
  textMuted,
  canDelete,
  loading,
  onDeleteRow,
  onGenerateLineItemInvoice,
  onUtilityUnfreeze,
  onUtilitySave,
  onUtilityPass,
  onFreezeAllUtilityRows,
  billingLinesFrozen,
  onUnfreezeBillingLineRow,
  onUnfreezeBillingLineGroup,
  activeTab,
  onTabChange,
  pageSize = DEFAULT_PAGE_SIZE,
  /** When set, only this dataset is shown and the tab strip is hidden (embedded panel). */
  singleTabId,
  /** Subset of tabs to show (tab buttons). Ignored when `singleTabId` is set. */
  visibleTabIds,
  /** Parsed-invoices table: sort by `parse_started_at` descending (then issue rows first as tie-breaker). */
  parsedSortByParseStarted,
  /** For the parsed tab, format these columns in the browser local timezone. */
  parsedTimestampColumns,
  /** Parsed-invoices panel only: reload rows from the server (e.g. after async parse completes). */
  onRefreshParsedData,
}: {
  bundle: SessionDetailBundle;
  textPrimary: string;
  textMuted: string;
  canDelete?: boolean;
  loading?: boolean;
  onDeleteRow?: (tab: TabId, row: Row) => void;
  onGenerateLineItemInvoice?: (row: Row) => void;
  onUtilityUnfreeze?: (row: Row) => void;
  onUtilitySave?: (row: Row, payload: Record<string, unknown>) => void;
  onUtilityPass?: (row: Row) => void;
  onFreezeAllUtilityRows?: () => void;
  /** When true, line-item rows cannot be deleted from the UI (matches frozen billing state). */
  billingLinesFrozen?: boolean;
  /** Superuser: unfreeze one billing line item (same API as bulk unfreeze, scoped by line id). */
  onUnfreezeBillingLineRow?: (row: Row) => void;
  /** Superuser: unfreeze every line in the same asset + utility PDF group (`line_group_key`). */
  onUnfreezeBillingLineGroup?: (groupKey: string) => void | Promise<void>;
  /** Optional external tab control from parent. */
  activeTab?: TabId;
  onTabChange?: (t: TabId) => void;
  pageSize?: number;
  singleTabId?: TabId;
  visibleTabIds?: TabId[];
  parsedSortByParseStarted?: boolean;
  parsedTimestampColumns?: string[];
  onRefreshParsedData?: () => void | Promise<void>;
}) {
  const tabList = useMemo(() => {
    if (singleTabId) return TABS.filter((t) => t.id === singleTabId);
    if (visibleTabIds?.length)
      return TABS.filter((t) => visibleTabIds.includes(t.id));
    return TABS;
  }, [singleTabId, visibleTabIds]);

  const [tab, setTab] = useState<TabId>('lines');
  const [page, setPage] = useState(1);
  const [showFailedLinesOnly, setShowFailedLinesOnly] = useState(false);
  const [parsedIssueFilter, setParsedIssueFilter] = useState<'all' | 'failed' | 'security' | 'cycle' | 'merge'>('all');
  /** Empty = show all utility rows. When set (e.g. 80), only rows with parse_document_confidence_score strictly below this value are shown (low-confidence review). */
  const [utilityConfidenceMax, setUtilityConfidenceMax] = useState('');
  const [editingUtilityIds, setEditingUtilityIds] = useState<Record<string, boolean>>({});
  const [utilityDrafts, setUtilityDrafts] = useState<Record<string, Record<string, unknown>>>({});
  const [utilityReasonDrafts, setUtilityReasonDrafts] = useState<Record<string, string>>({});
  const [utilityRelinkPdfIdDrafts, setUtilityRelinkPdfIdDrafts] = useState<Record<string, string>>({});
  const [utilityExpandedIds, setUtilityExpandedIds] = useState<Record<string, boolean>>({});
  /** Full row including raw_text / parse JSON (lazy-loaded; omitted from session list API). */
  const [utilityBlobCache, setUtilityBlobCache] = useState<Record<string, Record<string, unknown>>>({});
  const [utilityBlobLoading, setUtilityBlobLoading] = useState<Record<string, boolean>>({});
  const [utilityBlobError, setUtilityBlobError] = useState<Record<string, string>>({});

  const utilityBundleSig = useMemo(
    () =>
      (bundle.utility_invoices || [])
        .map((r) => `${String(r.id ?? '')}:${String(r.updated_at ?? '')}`)
        .join('|'),
    [bundle.utility_invoices],
  );

  useEffect(() => {
    setUtilityBlobCache({});
    setUtilityBlobError({});
  }, [utilityBundleSig]);

  const loadUtilityBlobFields = useCallback(async (invoiceId: string) => {
    setUtilityBlobError((prev) => {
      const n = { ...prev };
      delete n[invoiceId];
      return n;
    });
    setUtilityBlobLoading((prev) => ({ ...prev, [invoiceId]: true }));
    try {
      const res = await fetchUtilityInvoiceDetail(invoiceId);
      if (!res.success) {
        setUtilityBlobError((prev) => ({
          ...prev,
          [invoiceId]: res.message || 'Failed to load full utility row',
        }));
        return;
      }
      setUtilityBlobCache((prev) => ({ ...prev, [invoiceId]: res.utility_invoice }));
    } finally {
      setUtilityBlobLoading((prev) => ({ ...prev, [invoiceId]: false }));
    }
  }, []);

  useEffect(() => {
    for (const id of Object.keys(utilityExpandedIds)) {
      if (!utilityExpandedIds[id]) continue;
      if (utilityBlobError[id]) continue;
      if (utilityBlobCache[id]) continue;
      if (utilityBlobLoading[id]) continue;
      void loadUtilityBlobFields(id);
    }
  }, [utilityExpandedIds, utilityBlobCache, utilityBlobLoading, utilityBlobError, loadUtilityBlobFields]);

  const tabListKey = tabList.map((t) => t.id).join('|');

  // Parent-controlled tab, single-tab embed mode, or clamp to allowed tabs.
  useEffect(() => {
    if (singleTabId) {
      setTab(singleTabId);
      return;
    }
    if (activeTab && tabList.some((t) => t.id === activeTab)) {
      setTab(activeTab);
      return;
    }
    setTab((prev) => (tabList.some((t) => t.id === prev) ? prev : tabList[0]?.id ?? 'lines'));
  }, [singleTabId, activeTab, tabListKey]);

  const rowsFor = (id: TabId): Row[] => {
    switch (id) {
      case 'parsed':
        return (bundle.upload_summary && bundle.upload_summary.length ? bundle.upload_summary : bundle.parsed_invoices) || [];
      case 'lines':
        return bundle.line_items || [];
      case 'utility':
        return bundle.utility_invoices || [];
      case 'generated':
        return (bundle.generated_invoices || []).map((r) => ({
          ...r,
          download: `/energy-revenue-hub/api/generated-invoices/${r.id}/download/`,
        }));
      case 'payments':
        return bundle.payments || [];
      case 'meters':
        return bundle.meter_readings || [];
      case 'generation':
        return bundle.asset_generation || [];
      case 'penalties':
        return bundle.penalties || [];
      case 'adjustments':
        return bundle.adjustments || [];
      case 'audit':
        return bundle.billing_audit_logs || [];
      default:
        return [];
    }
  };
  const parsedIssueCounts = useMemo(() => {
    const rows = rowsFor('parsed');
    let failed = 0;
    let security = 0;
    let cycle = 0;
    let merge = 0;
    for (const r of rows) {
      const parseStatus = String(r.parse_status || '').toLowerCase();
      const securityStatus = String(r.security_status || '').toLowerCase();
      const cycleAligned = String(r.billing_cycle_aligned ?? 'true').toLowerCase();
      const frozenChanged = String(r.frozen_data_changed ?? 'false').toLowerCase() === 'true';
      const patch = r.pending_utility_patch_json;
      const hasPatch = Boolean(patch && typeof patch === 'object' && Object.keys(patch as Record<string, unknown>).length > 0);
      if (parseStatus === 'failed') failed += 1;
      if (['failed', 'rejected', 'quarantine', 'quarantined'].includes(securityStatus)) security += 1;
      if (cycleAligned === 'false' || cycleAligned === '0') cycle += 1;
      if (hasPatch || frozenChanged) merge += 1;
    }
    return {
      all: rows.length,
      failed,
      security,
      cycle,
      merge,
    };
  }, [bundle]);

  const hasParsedIssue = (r: Row): boolean => {
    const parseStatus = String(r.parse_status || '').toLowerCase();
    const securityStatus = String(r.security_status || '').toLowerCase();
    const cycleAligned = String(r.billing_cycle_aligned ?? 'true').toLowerCase();
    const frozenChanged = String(r.frozen_data_changed ?? 'false').toLowerCase() === 'true';
    const patch = r.pending_utility_patch_json;
    const hasPatch = Boolean(patch && typeof patch === 'object' && Object.keys(patch as Record<string, unknown>).length > 0);
    return (
      parseStatus === 'failed' ||
      ['failed', 'rejected', 'quarantine', 'quarantined'].includes(securityStatus) ||
      cycleAligned === 'false' ||
      cycleAligned === '0' ||
      frozenChanged ||
      hasPatch
    );
  };

  const hasUtilityIssue = (r: Row): boolean => {
    const invoiceNumber = String(r.invoice_number || '').trim();
    const invoiceDate = String(r.invoice_date || '').trim();
    const parseStatus = String(r.parse_status || '').toLowerCase();
    return !invoiceNumber || !invoiceDate || parseStatus === 'failed';
  };

  const sortIssueAndFrozenFirst = (rows: Row[], issueFn: (r: Row) => boolean) => {
    return [...rows].sort((a, b) => {
      const aIssue = issueFn(a) ? 0 : 1;
      const bIssue = issueFn(b) ? 0 : 1;
      if (aIssue !== bIssue) return aIssue - bIssue;
      const aFrozen = String(a.is_frozen ?? 'false').toLowerCase() === 'true' ? 1 : 0;
      const bFrozen = String(b.is_frozen ?? 'false').toLowerCase() === 'true' ? 1 : 0;
      if (aFrozen !== bFrozen) return aFrozen - bFrozen;
      const aTime = String(a.updated_at || a.created_at || a.timestamp || '');
      const bTime = String(b.updated_at || b.created_at || b.timestamp || '');
      return bTime.localeCompare(aTime);
    });
  };

  const uploadPdfOptions = useMemo(() => {
    const rows = (bundle.upload_summary || []) as Row[];
    return rows
      .map((r) => ({
        id: String(r.billing_invoice_pdf_id || ''),
        name: String(r.original_filename || ''),
      }))
      .filter((r) => Boolean(r.id))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [bundle.upload_summary]);

  const preferred: Record<TabId, string[]> = {
    parsed: [
      'billing_invoice_pdf_id',
      'original_filename',
      'parse_status',
      'parse_error',
      'parse_started_at',
      'parse_completed_at',
      'parse_elapsed_seconds',
      'security_status',
      'security_reason_code',
      'parse_summary_status',
      'billing_cycle_aligned',
      'billing_cycle_warning_message',
      'frozen_data_changed',
      'transfer_status',
      'local_file_exists',
      'local_file_size_bytes',
      'invoice_number',
      'invoice_date',
      'period_start',
      'period_end',
      'asset_name',
      'total_amount',
      'confidence_score',
      'download_original',
      'created_at',
    ],
    lines: [
      'id',
      'sort_order',
      'line_kind',
      'segment_index',
      'leasing_year_label',
      'period_start',
      'period_end',
      'asset_name',
      'asset_code',
      'utility_billing_invoice_pdf_id',
      'actual_kwh',
      'export_kwh',
      'invoice_kwh',
      'ppa_rate',
      'revenue',
      'amount_excl_gst',
      'export_invoice_kwh',
      'export_rate',
      'export_amount',
      'invoice_generation_status',
      'invoice_generation_error',
      'billing_cycle_warning',
      'latest_generated_invoice_download',
      'line_extras_json',
      'is_frozen',
      'frozen_at',
      'frozen_by',
    ],
    // Omit raw_text / parse_* JSON from the main grid — they are huge OCR blobs and blow up row height.
    // They appear under "Manual entry form" in scrollable panels.
    utility: [
      'invoice_number',
      'account_no',
      'asset_code',
      'parse_review_status',
      'parse_review_passed_at',
      'parse_review_passed_by',
      'is_frozen',
      'vendor_key',
      'invoice_date',
      'period_start',
      'period_end',
      'currency_code',
      'total_amount',
      'export_energy',
      'export_energy_cost',
      'recurring_charges_dollars',
      'unit_rate',
      'calculated_unit_rate',
      'anomaly_flag',
      'current_charges_excl_gst',
      'net_unit_rate',
      'gst_rate',
      'parse_extraction_path',
      'parse_document_confidence_score',
      'parse_document_confidence_level',
      'loss_calculation_task_id',
      'invoice_record_type',
      'id',
      'billing_session_id',
      'billing_invoice_pdf_id',
      'frozen_at',
      'frozen_by',
      'created_at',
      'updated_at',
    ],
    generated: [
      'id',
      'version',
      'download',
      'file_path',
      'generated_at',
      'sharepoint_upload_status',
      'sharepoint_upload_error',
      'invoice_snapshot_json',
    ],
    payments: [
      'payment_id',
      'asset_number',
      'invoice_id',
      'payment_due',
      'payment_date',
      'payment_paid',
      'payment_pending',
      'payment_status',
    ],
    meters: [
      'id',
      'device_id',
      'read_at',
      'cumulative_value',
      'source',
      'data_quality',
      'reading_role',
      'period_label',
      'delta_kwh_for_period',
      'notes',
      'created_at',
    ],
    generation: ['id', 'asset_number', 'month', 'grid_export_kwh', 'pv_generation_kwh', 'rooftop_self_consumption_kwh', 'bess_dispatch_kwh'],
    penalties: ['id', 'asset_number', 'penalty_type', 'penalty_rate', 'penalty_charges'],
    adjustments: ['id', 'asset_number', 'adjustment_type', 'adjustment_amount', 'adjustment_reason'],
    audit: ['id', 'timestamp', 'action', 'performed_by', 'details'],
  };

  const allRows = useMemo(() => {
    const baseRows = rowsFor(tab);
    let filtered = baseRows;
    if (tab === 'parsed' && parsedIssueFilter !== 'all') {
      filtered = baseRows.filter((r) => {
        const parseStatus = String(r.parse_status || '').toLowerCase();
        const securityStatus = String(r.security_status || '').toLowerCase();
        const cycleAligned = String(r.billing_cycle_aligned ?? 'true').toLowerCase();
        const frozenChanged = String(r.frozen_data_changed ?? 'false').toLowerCase() === 'true';
        const patch = r.pending_utility_patch_json;
        const hasPatch = Boolean(patch && typeof patch === 'object' && Object.keys(patch as Record<string, unknown>).length > 0);
        if (parsedIssueFilter === 'failed') {
          return parseStatus === 'failed';
        }
        if (parsedIssueFilter === 'security') {
          return ['failed', 'rejected', 'quarantine', 'quarantined'].includes(securityStatus);
        }
        if (parsedIssueFilter === 'cycle') {
          return cycleAligned === 'false' || cycleAligned === '0';
        }
        if (parsedIssueFilter === 'merge') {
          return hasPatch || frozenChanged;
        }
        return true;
      });
    }
    if (tab === 'lines' && showFailedLinesOnly) {
      filtered = baseRows.filter((r) => String(r.invoice_generation_status || '').toLowerCase() === 'failed');
    }
    if (tab === 'utility') {
      const cap = asNumber(utilityConfidenceMax);
      if (cap != null) {
        filtered = baseRows.filter((r) => {
          const score = asNumber(r.parse_document_confidence_score);
          if (score == null) return true;
          return score < cap;
        });
      }
    }
    if (tab === 'parsed') {
      if (parsedSortByParseStarted) {
        return [...filtered].sort((a, b) => {
          const dt = parseStartedAtMs(b) - parseStartedAtMs(a);
          if (dt !== 0) return dt;
          const ai = hasParsedIssue(a) ? 0 : 1;
          const bi = hasParsedIssue(b) ? 0 : 1;
          return ai - bi;
        });
      }
      return sortIssueAndFrozenFirst(filtered, hasParsedIssue);
    }
    if (tab === 'lines') return sortBillingLineRowsByGroup(filtered);
    if (tab === 'utility') return sortIssueAndFrozenFirst(filtered, hasUtilityIssue);
    return filtered;
  }, [tab, bundle, showFailedLinesOnly, utilityConfidenceMax, parsedIssueFilter, parsedSortByParseStarted]);

  /** Tab badges must match what the table shows (same filters as allRows for each tab). */
  const filteredCounts = useMemo(() => {
    const parsedBase = (bundle.upload_summary && bundle.upload_summary.length ? bundle.upload_summary : bundle.parsed_invoices) || [];
    let parsedLen = parsedBase.length;
    if (parsedIssueFilter !== 'all') {
      parsedLen = parsedBase.filter((r) => {
        const parseStatus = String(r.parse_status || '').toLowerCase();
        const securityStatus = String(r.security_status || '').toLowerCase();
        const cycleAligned = String(r.billing_cycle_aligned ?? 'true').toLowerCase();
        const frozenChanged = String(r.frozen_data_changed ?? 'false').toLowerCase() === 'true';
        const patch = r.pending_utility_patch_json;
        const hasPatch = Boolean(patch && typeof patch === 'object' && Object.keys(patch as Record<string, unknown>).length > 0);
        if (parsedIssueFilter === 'failed') return parseStatus === 'failed';
        if (parsedIssueFilter === 'security') {
          return ['failed', 'rejected', 'quarantine', 'quarantined'].includes(securityStatus);
        }
        if (parsedIssueFilter === 'cycle') return cycleAligned === 'false' || cycleAligned === '0';
        if (parsedIssueFilter === 'merge') return hasPatch || frozenChanged;
        return true;
      }).length;
    }
    const lineBase = bundle.line_items || [];
    const linesLen = showFailedLinesOnly
      ? lineBase.filter((r) => String(r.invoice_generation_status || '').toLowerCase() === 'failed').length
      : lineBase.length;
    const utilBase = bundle.utility_invoices || [];
    const cap = asNumber(utilityConfidenceMax);
    const utilityLen =
      cap == null
        ? utilBase.length
        : utilBase.filter((r) => {
            const score = asNumber(r.parse_document_confidence_score);
            if (score == null) return true;
            return score < cap;
          }).length;
    return {
      parsed: parsedLen,
      lines: linesLen,
      utility: utilityLen,
      generated: bundle.generated_invoices?.length ?? 0,
      payments: bundle.payments?.length ?? 0,
      meters: bundle.meter_readings?.length ?? 0,
      generation: bundle.asset_generation?.length ?? 0,
      penalties: bundle.penalties?.length ?? 0,
      adjustments: bundle.adjustments?.length ?? 0,
      audit: bundle.billing_audit_logs?.length ?? 0,
    };
  }, [bundle, showFailedLinesOnly, utilityConfidenceMax, parsedIssueFilter]);

  useEffect(() => {
    setPage(1);
  }, [tab, showFailedLinesOnly, parsedIssueFilter, utilityConfidenceMax]);

  const total = allRows.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages);

  useEffect(() => {
    if (page !== safePage) {
      setPage(safePage);
    }
  }, [page, safePage]);

  const pagedRows = useMemo(
    () => allRows.slice((safePage - 1) * pageSize, safePage * pageSize),
    [allRows, safePage, pageSize]
  );

  const linesGroupHeaderRender = useMemo(() => {
    return ({ groupKey, firstRow }: { groupKey: string; groupOrdinal: number; firstRow: Row }) => {
      const parts = groupKey.split('|');
      const assetPart = parts[0] || '—';
      const pdfPart = parts[1] || '';
      const pdfShort =
        !pdfPart || pdfPart === 'none' ? '—' : pdfPart.length > 14 ? `${pdfPart.slice(0, 10)}…` : pdfPart;
      return (
        <div
          className="d-flex flex-wrap align-items-center gap-2 px-2 py-1"
          style={{
            background: 'rgba(15, 23, 42, 0.72)',
            borderLeft: '3px solid rgba(59, 130, 246, 0.85)',
          }}
        >
          <span className="small" style={{ color: textMuted }}>
            Asset + utility PDF ·{' '}
            <span style={{ color: textPrimary, fontWeight: 600 }}>{assetPart}</span>
            <span className="mx-1" style={{ color: textMuted }}>
              ·
            </span>
            <span title={pdfPart} style={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.75rem' }}>
              {pdfShort}
            </span>
          </span>
          <div className="d-flex flex-wrap gap-1">
            {canDelete && onUnfreezeBillingLineGroup && (
              <button
                type="button"
                className="btn btn-sm btn-warning text-dark fw-semibold"
                style={{ boxShadow: '0 1px 3px rgba(217, 119, 6, 0.45)' }}
                disabled={loading}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  void onUnfreezeBillingLineGroup(groupKey);
                }}
              >
                Unfreeze group
              </button>
            )}
            {onGenerateLineItemInvoice && (
              <button
                type="button"
                className="btn btn-sm btn-primary fw-semibold"
                style={{ boxShadow: '0 1px 3px rgba(37, 99, 235, 0.45)' }}
                disabled={loading || !String(firstRow?.id ?? '').trim()}
                title={
                  String(firstRow?.id ?? '').trim()
                    ? 'Generate PDF for this asset + utility PDF group (same as row action)'
                    : 'Missing line id — refresh the page'
                }
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  void onGenerateLineItemInvoice(firstRow);
                }}
              >
                Generate group PDF
              </button>
            )}
          </div>
        </div>
      );
    };
  }, [canDelete, loading, onGenerateLineItemInvoice, onUnfreezeBillingLineGroup, textMuted, textPrimary]);

  const tableEmptyMessage = useMemo(() => {
    const parsedBaseLen =
      (bundle.upload_summary && bundle.upload_summary.length ? bundle.upload_summary : bundle.parsed_invoices)?.length ?? 0;
    if (tab === 'lines' && showFailedLinesOnly && (bundle.line_items || []).length > 0 && total === 0) {
      return 'No billing lines with failed PDF generation. Uncheck "Show failed PDF rows only" to see all lines.';
    }
    if (tab === 'utility' && asNumber(utilityConfidenceMax) != null && (bundle.utility_invoices || []).length > 0 && total === 0) {
      return 'No utility invoices below this confidence threshold. Raise the value or clear the field to see all rows.';
    }
    if (tab === 'parsed' && parsedIssueFilter !== 'all' && parsedBaseLen > 0 && total === 0) {
      return 'No rows match this issue filter. Choose "All" or another filter to see parsed invoices.';
    }
    return 'No rows for this tab.';
  }, [tab, total, showFailedLinesOnly, bundle, utilityConfidenceMax, parsedIssueFilter]);

  const showDeleteColumn = Boolean(canDelete && onDeleteRow && tab !== 'audit');
  const showLineGenerateColumn = tab === 'lines' && Boolean(onGenerateLineItemInvoice);
  const linesExtraRowButtons = useMemo(() => {
    if (!canDelete || !onUnfreezeBillingLineRow) return undefined;
    return [
      {
        label: 'Unfreeze',
        onClick: onUnfreezeBillingLineRow,
        visible: (row: Row) => isBillingLineRowFrozen(row),
        disabled: (_row: Row) => Boolean(loading),
      },
    ];
  }, [canDelete, onUnfreezeBillingLineRow, loading]);
  const showActions =
    showDeleteColumn ||
    showLineGenerateColumn ||
    (tab === 'lines' && Boolean(canDelete && onUnfreezeBillingLineRow));

  const utilityEditableFields = [
    'invoice_number',
    'account_no',
    'asset_code',
    'vendor_key',
    'invoice_date',
    'period_start',
    'period_end',
    'currency_code',
    'total_amount',
    'export_energy',
    'export_energy_cost',
    'recurring_charges_dollars',
    'unit_rate',
    'current_charges_excl_gst',
    'gst_rate',
  ];

  const utilityManualEntryFields = [
    ...utilityEditableFields,
    'raw_text',
    'parse_page_scores_json',
    'parse_block_confidence_json',
  ] as const;

  const utilityBlobManualFields = new Set([
    'raw_text',
    'parse_page_scores_json',
    'parse_block_confidence_json',
  ]);

  const utilityRequiredFields = ['asset_code', 'invoice_number', 'invoice_date'] as const;

  const isMissingRequired = (field: (typeof utilityRequiredFields)[number], value: unknown): boolean => {
    if (field === 'invoice_date') return !String(value ?? '').trim();
    return !String(value ?? '').trim();
  };

  const showTabStrip = !singleTabId && tabList.length > 1;

  const parsedTsKeys =
    tab === 'parsed' && parsedTimestampColumns?.length
      ? parsedTimestampColumns
      : undefined;

  /** ISO timestamps shown in the browser's local timezone (generated, audit, utility, etc.). */
  const mergedTableTimestampKeys = useMemo(() => {
    const keys = new Set<string>([
      'generated_at',
      'created_at',
      'updated_at',
      'frozen_at',
      'parse_review_passed_at',
      'timestamp',
      'read_at',
      'payment_due',
      'payment_date',
    ]);
    if (parsedTsKeys) {
      for (const k of parsedTsKeys) {
        keys.add(k);
      }
    }
    return Array.from(keys);
  }, [parsedTsKeys]);

  return (
    <div className="erh-session-tabs">
      {showTabStrip && (
        <div
          className="d-flex flex-wrap gap-1 mb-2"
          role="tablist"
          style={{ rowGap: '6px', borderBottom: '1px solid rgba(148,163,184,0.25)', paddingBottom: 8 }}
        >
          {tabList.map(({ id, label }) => {
            const n = filteredCounts[id];
            const active = tab === id;
            return (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={active}
                className="btn btn-sm"
                onClick={() => {
                  setTab(id);
                  onTabChange?.(id);
                }}
                style={{
                  borderRadius: 8,
                  border: active ? '1px solid rgba(59,130,246,0.6)' : '1px solid rgba(148,163,184,0.35)',
                  background: active ? 'rgba(59,130,246,0.15)' : 'transparent',
                  color: textPrimary,
                  fontWeight: active ? 600 : 400,
                }}
              >
                {label}
                <span className="ms-1" style={{ color: textMuted, fontSize: '0.75rem' }}>
                  ({n})
                </span>
              </button>
            );
          })}
        </div>
      )}
      {billingLinesFrozen && tab === 'lines' && (
        <div
          className="mb-2 px-2 py-2 rounded"
          style={{
            background: 'rgba(234,179,8,0.12)',
            border: '1px solid rgba(234,179,8,0.35)',
            color: textPrimary,
            fontSize: '0.85rem',
          }}
        >
          Billing lines are frozen (issued invoice snapshot). You cannot delete a line until it is unfrozen.
          Use <strong>Unfreeze</strong> on the row or <strong>Unfreeze billing lines</strong> in workflow actions,
          then fix sources and recalculate if needed.
        </div>
      )}
      <div role="tabpanel" className="pt-1">
        {tab === 'lines' && (
          <label className="d-flex align-items-center gap-2 mb-2" style={{ color: textMuted, fontSize: '0.85rem' }}>
            <input
              type="checkbox"
              checked={showFailedLinesOnly}
              onChange={(e) => setShowFailedLinesOnly(e.target.checked)}
              disabled={loading}
            />
            Show failed PDF rows only
          </label>
        )}
        {tab === 'parsed' && (
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span style={{ color: textMuted, fontSize: '0.85rem' }}>Issue filter</span>
            {[
              { key: 'all', label: 'All' },
              { key: 'failed', label: 'Parse failed' },
              { key: 'security', label: 'Security blocked' },
              { key: 'cycle', label: 'Cycle mismatch' },
              { key: 'merge', label: 'Pending merge' },
            ].map((opt) => (
              <button
                key={opt.key}
                type="button"
                className="btn btn-sm"
                disabled={loading}
                onClick={() => setParsedIssueFilter(opt.key as 'all' | 'failed' | 'security' | 'cycle' | 'merge')}
                style={{
                  borderRadius: 8,
                  border:
                    parsedIssueFilter === opt.key
                      ? '1px solid rgba(59,130,246,0.6)'
                      : '1px solid rgba(148,163,184,0.35)',
                  background: parsedIssueFilter === opt.key ? 'rgba(59,130,246,0.12)' : 'transparent',
                  color: textPrimary,
                  fontSize: '0.8rem',
                }}
              >
                {opt.label}
                <span className="ms-1" style={{ color: textMuted, fontSize: '0.75rem' }}>
                  (
                  {opt.key === 'all'
                    ? parsedIssueCounts.all
                    : opt.key === 'failed'
                      ? parsedIssueCounts.failed
                      : opt.key === 'security'
                        ? parsedIssueCounts.security
                        : opt.key === 'cycle'
                          ? parsedIssueCounts.cycle
                          : parsedIssueCounts.merge}
                  )
                </span>
              </button>
            ))}
            {onRefreshParsedData ? (
              <button
                type="button"
                className="btn btn-sm btn-secondary ms-auto"
                disabled={loading}
                title="Reload parse status and rows from the server without refreshing the page"
                onClick={() => void onRefreshParsedData()}
              >
                Refresh table
              </button>
            ) : null}
          </div>
        )}
        {tab === 'utility' && (
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <label className="d-flex align-items-center gap-2 mb-0" style={{ color: textMuted, fontSize: '0.85rem' }}>
              Confidence below (optional)
              <input
                className="ui-input"
                style={{ width: 90 }}
                placeholder="all"
                title="Leave empty to list every utility invoice. Set a number to show only rows with confidence score below that value (for reviewing uncertain parses)."
                value={utilityConfidenceMax}
                onChange={(e) => setUtilityConfidenceMax(e.target.value)}
                disabled={loading}
              />
            </label>
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              disabled={loading || !onFreezeAllUtilityRows}
              onClick={() => onFreezeAllUtilityRows?.()}
            >
              Freeze all utility rows
            </button>
          </div>
        )}
        <div className="d-flex justify-content-end align-items-center gap-2 mb-2">
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={loading || total === 0}
            title="Download all rows for this tab as CSV (current filters and sort). Uses data already loaded for this ERH session."
            onClick={() => {
              if (allRows.length === 0) return;
              const csv = rowsToCsv(allRows, preferred[tab]);
              const prefix = billingSessionIdForFilename(bundle);
              const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
              triggerCsvDownload(`erh-${tab}-${prefix}-${stamp}.csv`, csv);
            }}
          >
            Download CSV ({total})
          </button>
        </div>
        {tab !== 'utility' ? (
          <ErhDataTable
            rows={pagedRows}
            preferredKeys={preferred[tab]}
            emptyMessage={tableEmptyMessage}
            textPrimary={textPrimary}
            textMuted={textMuted}
            showActions={showActions}
            loading={loading}
            onDeleteRow={onDeleteRow && showDeleteColumn ? (row) => onDeleteRow(tab, row) : undefined}
            extraRowActionLabel={showLineGenerateColumn ? 'Generate row PDF' : undefined}
            onExtraRowAction={showLineGenerateColumn ? onGenerateLineItemInvoice : undefined}
            isExtraRowActionDisabled={showLineGenerateColumn ? () => false : undefined}
            extraRowButtons={tab === 'lines' ? linesExtraRowButtons : undefined}
            isRowDeleteDisabled={tab === 'lines' ? (row) => isBillingLineRowFrozen(row) : undefined}
            timestampColumnKeys={mergedTableTimestampKeys}
            lineGroupKey={tab === 'lines' ? lineGroupKeyForErhLineRow : undefined}
            renderGroupHeaderRow={tab === 'lines' ? linesGroupHeaderRender : undefined}
          />
        ) : (
          <div className="erh-table-wrap" style={{ overflowX: 'auto', maxWidth: '100%' }}>
            {(() => {
              const utilityStickyBg = 'rgb(15, 23, 42)';
              const utilityStickyHeadBg = 'rgb(17, 24, 39)';
              return (
            <table className="table table-sm align-middle mb-0" style={{ color: textPrimary, minWidth: 720, fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(148,163,184,0.35)' }}>
                  {preferred.utility.map((k) => (
                    <th
                      key={k}
                      className="text-nowrap px-2 py-2"
                      style={{ fontWeight: 600, maxWidth: utilityColumnMaxWidthPx(k), verticalAlign: 'bottom' }}
                    >
                      {k.replace(/_/g, ' ')}
                    </th>
                  ))}
                  <th
                    className="px-2 py-2"
                    style={{
                      fontWeight: 600,
                      position: 'sticky',
                      right: 0,
                      zIndex: 3,
                      minWidth: 212,
                      width: 220,
                      verticalAlign: 'bottom',
                      background: utilityStickyHeadBg,
                      boxShadow: '-1px 0 0 rgba(148,163,184,0.35)',
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {pagedRows.map((row, i) => {
                  const id = String(primaryRowId(row) ?? `row-${i}`);
                  const isFrozen = Boolean(row.is_frozen);
                  const isUnresolved = Boolean((row as any).is_unresolved);
                  const reviewStatus = String((row as any).parse_review_status || '').toLowerCase();
                  const isPassed = reviewStatus === 'passed';
                  const editing = Boolean(editingUtilityIds[id]) && !isFrozen;
                  const expanded = Boolean(utilityExpandedIds[id]) && !isFrozen;
                  const draft = utilityDrafts[id] || {};
                  const reason = utilityReasonDrafts[id] || '';
                  const relinkPdfId = utilityRelinkPdfIdDrafts[id] || '';
                  return (
                    <Fragment key={id}>
                      <tr style={{ borderBottom: '1px solid rgba(148,163,184,0.2)' }}>
                        {preferred.utility.map((k) => {
                          const editable = utilityEditableFields.includes(k);
                          const raw = (draft[k] ?? row[k]) as unknown;
                          const mw = utilityColumnMaxWidthPx(k);
                          return (
                            <td
                              key={k}
                              className="px-2 py-1 align-top"
                              style={{ maxWidth: mw, verticalAlign: 'top' }}
                            >
                              {editing && editable ? (
                                <input
                                  className="ui-input"
                                  style={{ width: '100%', minWidth: 0, maxWidth: Math.max(mw, 220) }}
                                  value={String(raw ?? '')}
                                  onChange={(e) =>
                                    setUtilityDrafts((prev) => ({
                                      ...prev,
                                      [id]: { ...(prev[id] || {}), [k]: e.target.value },
                                    }))
                                  }
                                />
                              ) : (
                                utilityCellInner(k, raw, { textMuted, textPrimary })
                              )}
                            </td>
                          );
                        })}
                        <td
                          className="px-2 py-2 align-top"
                          style={{
                            position: 'sticky',
                            right: 0,
                            zIndex: 2,
                            minWidth: 212,
                            width: 220,
                            background: utilityStickyBg,
                            boxShadow: '-1px 0 0 rgba(148,163,184,0.25)',
                            verticalAlign: 'top',
                          }}
                        >
                        <div className="d-flex flex-column gap-1" style={{ maxWidth: 260 }}>
                        {isUnresolved && (
                          <div style={{ color: textMuted, fontSize: '0.72rem', whiteSpace: 'normal', lineHeight: 1.35 }}>
                            Unresolved. File: {String((row as any).source_original_filename || row.original_filename || '—')}
                          </div>
                        )}
                        {!isPassed && (
                          <div style={{ color: textMuted, fontSize: '0.72rem', whiteSpace: 'normal', lineHeight: 1.35 }}>
                            {isFrozen ? (
                              <>
                                Review <strong>pending</strong>. Frozen rows count as approved for billing once{' '}
                                <strong>asset code</strong> is set. Use <strong>Pass</strong> to clear the review flag, or{' '}
                                <strong>Unfreeze</strong> to edit fields.
                              </>
                            ) : (
                              <>
                                Review <strong>pending</strong>. Click <strong>Pass</strong> after checking the parse, or{' '}
                                <strong>freeze</strong> the row when data is final — billing can use frozen rows with a valid{' '}
                                <strong>asset code</strong>.
                              </>
                            )}
                          </div>
                        )}
                        {!isFrozen && (
                          <div>
                            <input
                              className="ui-input"
                              placeholder="Reason (required to save)"
                              value={reason}
                              onChange={(e) => setUtilityReasonDrafts((prev) => ({ ...prev, [id]: e.target.value }))}
                            />
                          </div>
                        )}
                        <div className="d-flex flex-wrap gap-1 align-items-center">
                        {isFrozen ? (
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            disabled={loading || !onUtilityUnfreeze}
                            onClick={() => {
                              setEditingUtilityIds((prev) => ({ ...prev, [id]: true }));
                              if (isUnresolved) {
                                setUtilityExpandedIds((prev) => ({ ...prev, [id]: true }));
                              }
                              onUtilityUnfreeze?.(row);
                            }}
                          >
                            Unfreeze
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            disabled={loading || !onUtilitySave || !reason.trim()}
                            onClick={() => {
                              onUtilitySave?.(row, { ...draft, reason });
                              setEditingUtilityIds((prev) => ({ ...prev, [id]: false }));
                              setUtilityDrafts((prev) => ({ ...prev, [id]: {} }));
                              setUtilityReasonDrafts((prev) => ({ ...prev, [id]: '' }));
                              setUtilityExpandedIds((prev) => ({ ...prev, [id]: false }));
                            }}
                          >
                            Save
                          </button>
                        )}
                        {!isFrozen && (
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-secondary"
                            disabled={loading}
                            onClick={() => {
                              setUtilityExpandedIds((prev) => {
                                const nextOpen = !Boolean(prev[id]);
                                if (!nextOpen) {
                                  setUtilityBlobCache((c) => {
                                    const n = { ...c };
                                    delete n[id];
                                    return n;
                                  });
                                  setUtilityBlobError((e) => {
                                    const n = { ...e };
                                    delete n[id];
                                    return n;
                                  });
                                  setUtilityBlobLoading((l) => {
                                    const n = { ...l };
                                    delete n[id];
                                    return n;
                                  });
                                }
                                return { ...prev, [id]: nextOpen };
                              });
                            }}
                          >
                            {expanded ? 'Hide form' : 'Manual entry'}
                          </button>
                        )}
                        {!isPassed && (
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-success"
                            disabled={loading || !onUtilityPass}
                            onClick={() => onUtilityPass?.(row)}
                          >
                            Pass
                          </button>
                        )}
                        {onDeleteRow && canDelete && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm"
                            disabled={loading}
                            onClick={() => onDeleteRow('utility', row)}
                          >
                            Delete
                          </button>
                        )}
                        </div>
                        {isUnresolved && !isFrozen && (
                          <div className="mt-1 d-flex flex-wrap gap-1">
                            <select
                              className="ui-input"
                              value={relinkPdfId}
                              onChange={(e) => setUtilityRelinkPdfIdDrafts((prev) => ({ ...prev, [id]: e.target.value }))}
                              style={{ minWidth: 180, flex: '1 1 160px' }}
                            >
                              <option value="">Relink to uploaded PDF…</option>
                              {uploadPdfOptions.map((o) => (
                                <option key={o.id} value={o.id}>
                                  {o.name || o.id}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-primary"
                              disabled={loading || !onUtilitySave || !reason.trim() || !relinkPdfId}
                              onClick={() => {
                                onUtilitySave?.(row, { action: 'relink', billing_invoice_pdf_id: relinkPdfId, reason });
                                setUtilityRelinkPdfIdDrafts((prev) => ({ ...prev, [id]: '' }));
                              }}
                            >
                              Relink
                            </button>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              disabled={loading || !onUtilitySave || !reason.trim()}
                              onClick={() => onUtilitySave?.(row, { action: 'mark_failed', reason })}
                            >
                              Mark failed
                            </button>
                          </div>
                        )}
                        </div>
                        </td>
                      </tr>
                      {expanded && (
                        <tr key={`${id}__form`} style={{ borderBottom: '1px solid rgba(148,163,184,0.2)' }}>
                          <td colSpan={preferred.utility.length + 1} className="px-2 py-2">
                            <div
                              className="rounded p-2"
                              style={{ border: '1px solid rgba(148,163,184,0.25)', background: 'rgba(148,163,184,0.05)' }}
                            >
                              <div className="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                                <div style={{ color: textPrimary, fontWeight: 600, fontSize: '0.9rem' }}>
                                  Manual entry (all fields)
                                </div>
                                <div style={{ color: textMuted, fontSize: '0.8rem' }}>
                                  Reason is required to save. Save will freeze the row.
                                </div>
                              </div>
                              <p className="mb-2" style={{ color: textMuted, fontSize: '0.78rem', lineHeight: 1.4 }}>
                                The list above omits large OCR and parse JSON fields for speed. They load here when you
                                open this panel.
                              </p>
                              {utilityBlobLoading[id] && (
                                <div className="mb-2" style={{ color: textMuted, fontSize: '0.78rem' }}>
                                  Loading raw text and parse JSON…
                                </div>
                              )}
                              {utilityBlobError[id] && (
                                <div className="mb-2" style={{ color: 'rgb(248, 113, 113)', fontSize: '0.78rem' }}>
                                  {utilityBlobError[id]}
                                </div>
                              )}
                              <div className="row g-2">
                                {utilityManualEntryFields.map((field) => {
                                  const blobRow = utilityBlobCache[id];
                                  const val = (draft[field] ?? blobRow?.[field] ?? (row as any)[field]) as unknown;
                                  if (utilityBlobManualFields.has(field)) {
                                    const isJson =
                                      field === 'parse_page_scores_json' || field === 'parse_block_confidence_json';
                                    const blobPending = Boolean(utilityBlobLoading[id]) && !blobRow;
                                    return (
                                      <div key={field} className="col-12">
                                        <label className="ui-label">{field.replace(/_/g, ' ')}</label>
                                        <textarea
                                          className="ui-input"
                                          rows={isJson ? 8 : 6}
                                          spellCheck={false}
                                          disabled={blobPending}
                                          style={{
                                            maxHeight: 220,
                                            overflow: 'auto',
                                            fontFamily: isJson ? 'ui-monospace, monospace' : undefined,
                                            fontSize: isJson ? '0.78rem' : undefined,
                                            whiteSpace: 'pre-wrap',
                                            wordBreak: 'break-word',
                                          }}
                                          value={blobPending ? '' : String(val ?? '')}
                                          onChange={(e) =>
                                            setUtilityDrafts((prev) => ({
                                              ...prev,
                                              [id]: { ...(prev[id] || {}), [field]: e.target.value },
                                            }))
                                          }
                                        />
                                      </div>
                                    );
                                  }
                                  const isRequired = (utilityRequiredFields as readonly string[]).includes(field);
                                  const missing = isRequired && isMissingRequired(field as any, val);
                                  return (
                                    <div key={field} className="col-md-4">
                                      <label className="ui-label">{field.replace(/_/g, ' ')}</label>
                                      <input
                                        className="ui-input"
                                        style={
                                          missing
                                            ? { borderColor: 'rgba(220,38,38,0.85)', boxShadow: '0 0 0 2px rgba(220,38,38,0.12)' }
                                            : undefined
                                        }
                                        value={String(val ?? '')}
                                        onChange={(e) =>
                                          setUtilityDrafts((prev) => ({
                                            ...prev,
                                            [id]: { ...(prev[id] || {}), [field]: e.target.value },
                                          }))
                                        }
                                      />
                                    </div>
                                  );
                                })}
                              </div>
                              <div className="hint-text mt-2">
                                Required: <strong>asset code</strong>, <strong>invoice number</strong>, <strong>invoice date</strong>.
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
              );
            })()}
          </div>
        )}
        {total > pageSize && (
          <div
            className="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-2 pt-2"
            style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}
          >
            <span style={{ color: textMuted, fontSize: '0.8rem' }}>
              Showing {(safePage - 1) * pageSize + 1}–{Math.min(safePage * pageSize, total)} of {total}
            </span>
            <div className="d-flex align-items-center gap-2">
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={safePage <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <span style={{ color: textMuted, fontSize: '0.85rem' }}>
                Page {safePage} / {totalPages}
              </span>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={safePage >= totalPages || loading}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
