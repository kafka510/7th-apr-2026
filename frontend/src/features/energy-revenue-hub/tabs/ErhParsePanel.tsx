import type { Dispatch, SetStateAction } from 'react';
import { SessionDataTabs, type SessionDetailBundle, type TabId } from '../SessionDataTabs';
import { PARSED_LOCAL_TS_COLUMNS } from '../erhTypes';

type UploadRow = {
  name: string;
  size: number;
  progress: number;
  status: 'pending' | 'uploading' | 'queued' | 'failed';
  reasonCode?: string;
  reasonMessage?: string;
};

type Props = {
  textPrimary: string;
  textMuted: string;
  loading: boolean;
  selectedSessionId: string;
  hasLocalFiles: boolean;
  localFilesSummary: {
    rows: Array<Record<string, unknown>>;
    count: number;
    totalBytes: number;
  };
  formatBytes: (n: number) => string;
  coverageSummary: Record<string, unknown>;
  pendingAssets: Array<Record<string, unknown>>;
  conflicts: Array<Record<string, unknown>>;
  conflictIds: string[];
  expandedConflictIds: string[];
  setExpandedConflictIds: Dispatch<SetStateAction<string[]>>;
  parseTimingSummary: { count: number; avg: number; min: number; max: number };
  refreshSessionDetail: (id: string) => Promise<void>;
  onResolveConflict: (id: string, action: 'apply' | 'reject') => Promise<void>;
  canDelete: boolean;
  setFiles: (f: FileList | null) => void;
  uploadRows: UploadRow[];
  setUploadRows: Dispatch<SetStateAction<UploadRow[]>>;
  onParseInvoices: () => Promise<void>;
  sessionDataBundle: SessionDetailBundle | null;
  canUnfreezeBillingLines: boolean;
  billingLinesFrozen: boolean;
  handleTabDelete: (tab: TabId, row: Record<string, unknown>) => Promise<void>;
  onGenerateLineItemPdf: (row: Record<string, unknown>) => Promise<void>;
  onUtilityUnfreeze: (row: Record<string, unknown>) => Promise<void>;
  onUtilitySave: (row: Record<string, unknown>, payload: Record<string, unknown>) => Promise<void>;
  onUtilityPass: (row: Record<string, unknown>) => Promise<void>;
  onFreezeAllUtilityRows: () => Promise<void>;
  onUnfreezeBillingLineRow: (row: Record<string, unknown>) => Promise<void>;
};

export function ErhParsePanel(props: Props) {
  const {
    textPrimary,
    textMuted,
    loading,
    selectedSessionId,
    hasLocalFiles,
    localFilesSummary,
    formatBytes,
    coverageSummary,
    pendingAssets,
    conflicts,
    conflictIds,
    expandedConflictIds,
    setExpandedConflictIds,
    parseTimingSummary,
    refreshSessionDetail,
    onResolveConflict,
    canDelete,
    setFiles,
    uploadRows,
    setUploadRows,
    onParseInvoices,
    sessionDataBundle,
    canUnfreezeBillingLines,
    billingLinesFrozen,
    handleTabDelete,
    onGenerateLineItemPdf,
    onUtilityUnfreeze,
    onUtilitySave,
    onUtilityPass,
    onFreezeAllUtilityRows,
    onUnfreezeBillingLineRow,
  } = props;

  return (
    <>
      <div
        className="mb-3 p-2 rounded"
        style={{
          border: hasLocalFiles ? '1px solid rgba(245,158,11,0.55)' : '1px solid rgba(148,163,184,0.3)',
          background: hasLocalFiles ? 'rgba(245,158,11,0.10)' : 'rgba(2,6,23,0.03)',
        }}
      >
        <div className="d-flex justify-content-between align-items-center gap-2 flex-wrap">
          <div className="hint-text">
            Local invoice files:{' '}
            <strong style={{ color: hasLocalFiles ? '#b45309' : textPrimary }}>{localFilesSummary.count}</strong> | Total size:{' '}
            <strong>{formatBytes(localFilesSummary.totalBytes)}</strong>
            {hasLocalFiles ? (
              <span className="ms-2 px-2 py-1 rounded" style={{ background: 'rgba(245,158,11,0.2)', color: '#92400e' }}>
                Cleanup pending
              </span>
            ) : null}
          </div>
          <div className="d-flex gap-2">
            {hasLocalFiles && (
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={loading}
                onClick={() => {
                  for (const r of localFilesSummary.rows) {
                    const id = String(r.billing_invoice_pdf_id || '').trim();
                    if (!id) continue;
                    const url = `/energy-revenue-hub/api/billing-invoice-pdfs/${id}/download-original/`;
                    window.open(url, '_blank', 'noopener,noreferrer');
                  }
                }}
              >
                Download all local-present files
              </button>
            )}
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={loading}
              onClick={() => selectedSessionId && void refreshSessionDetail(selectedSessionId)}
            >
              Refresh local file status
            </button>
          </div>
        </div>
        {localFilesSummary.count > 0 ? (
          <div className="mt-2" style={{ maxHeight: 140, overflowY: 'auto', fontSize: '0.82rem', color: textMuted }}>
            {localFilesSummary.rows.map((r, i) => (
              <div key={`${String(r.billing_invoice_pdf_id || i)}`} className="d-flex justify-content-between gap-2">
                <span>{String(r.original_filename || r.billing_invoice_pdf_id || `file_${i + 1}`)}</span>
                <span>{formatBytes(Number(r.local_file_size_bytes || 0))}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="hint-text mt-1">No local files currently present for this session.</div>
        )}
      </div>
      <div className="mb-3 p-2 rounded" style={{ border: '1px solid rgba(148,163,184,0.3)', background: 'rgba(2,6,23,0.03)' }}>
        <div className="d-flex flex-wrap gap-3 hint-text">
          <span>Coverage expected: <strong>{String(coverageSummary.expected_utility_assets_count ?? 0)}</strong></span>
          <span>Ready: <strong>{String(coverageSummary.ready_assets_count ?? 0)}</strong></span>
          <span>Pending assets: <strong>{pendingAssets.length}</strong></span>
          <span>Merge conflicts: <strong>{conflicts.length}</strong></span>
          <span>
            Parse timing: <strong>{parseTimingSummary.count}</strong> done | avg{' '}
            <strong>{parseTimingSummary.avg.toFixed(2)}s</strong> | min/max{' '}
            <strong>
              {parseTimingSummary.min.toFixed(2)}s/{parseTimingSummary.max.toFixed(2)}s
            </strong>
          </span>
        </div>
        {pendingAssets.length > 0 && (
          <div className="mt-2" style={{ color: '#b45309', fontSize: '0.82rem' }}>
            Pending assets: {pendingAssets.map((a) => String(a.asset_code || a.asset_name || 'asset')).join(', ')}
          </div>
        )}
        {conflicts.length > 0 && (
          <div className="mt-1" style={{ color: '#b91c1c', fontSize: '0.82rem' }}>
            <div className="mb-1">
              Pending merge conflicts:{' '}
              {conflicts.map((c) => String(c.source_original_filename || c.billing_invoice_pdf_id || 'file')).join(', ')}
            </div>
            <div className="d-flex gap-2 flex-wrap mb-1">
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={loading || conflictIds.length === 0}
                onClick={() => setExpandedConflictIds(conflictIds)}
              >
                Expand all diffs
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={loading || expandedConflictIds.length === 0}
                onClick={() => setExpandedConflictIds([])}
              >
                Collapse all diffs
              </button>
            </div>
            <div className="d-flex flex-column gap-1">
              {conflicts.map((c, idx) => {
                const id = String(c.billing_invoice_pdf_id || '').trim();
                if (!id) return null;
                return (
                  <div key={`${id}-${idx}`} className="d-flex align-items-center gap-2 flex-wrap">
                    <span style={{ color: textMuted }}>{String(c.source_original_filename || id)}</span>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={loading}
                      onClick={() =>
                        setExpandedConflictIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
                      }
                    >
                      {expandedConflictIds.includes(id) ? 'Hide diff' : 'View diff'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={loading || !canDelete}
                      onClick={() => void onResolveConflict(id, 'apply')}
                    >
                      Apply merge
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={loading || !canDelete}
                      onClick={() => void onResolveConflict(id, 'reject')}
                    >
                      Reject merge
                    </button>
                    {expandedConflictIds.includes(id) && (
                      <div
                        className="w-100 mt-1 p-2 rounded"
                        style={{
                          background: 'rgba(15,23,42,0.06)',
                          border: '1px solid rgba(148,163,184,0.28)',
                          color: textPrimary,
                          fontSize: '0.78rem',
                          overflowX: 'auto',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                      >
                        <div className="mb-1" style={{ color: textMuted }}>
                          Proposed patch
                        </div>
                        <pre className="mb-0" style={{ color: textPrimary }}>
                          {JSON.stringify((c.pending_utility_patch_json as Record<string, unknown>) || {}, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        <div className="mt-2 d-flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={loading}
            onClick={() => selectedSessionId && void refreshSessionDetail(selectedSessionId)}
          >
            Refresh readiness
          </button>
          {conflicts.length > 0 && (
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={loading}
              onClick={() => {
                for (const c of conflicts) {
                  const id = String(c.billing_invoice_pdf_id || '').trim();
                  if (!id) continue;
                  const url = `/energy-revenue-hub/api/billing-invoice-pdfs/${id}/download-original/`;
                  window.open(url, '_blank', 'noopener,noreferrer');
                }
              }}
            >
              Download conflicted originals
            </button>
          )}
        </div>
      </div>

      <div className="mb-3">
        <label className="ui-label">Utility invoice PDF(s)</label>
        <input
          type="file"
          accept=".pdf"
          multiple
          className="ui-input"
          onChange={(e) => {
            setFiles(e.target.files);
            const picked = Array.from(e.target.files || []);
            setUploadRows(picked.map((f) => ({ name: f.name, size: f.size, progress: 0, status: 'pending' })));
          }}
        />
        {uploadRows.length > 0 && (
          <div className="mt-2" style={{ maxHeight: 160, overflowY: 'auto' }}>
            {uploadRows.map((r, idx) => (
              <div key={`${r.name}-${idx}`} className="mb-1">
                <div className="d-flex justify-content-between" style={{ fontSize: '0.8rem', color: textMuted }}>
                  <span>{r.name}</span>
                  <span>
                    {formatBytes(r.size)} | {r.progress}% | {r.status}
                  </span>
                </div>
                <div style={{ height: 6, borderRadius: 4, background: 'rgba(148,163,184,0.3)' }}>
                  <div
                    style={{
                      width: `${r.progress}%`,
                      height: '100%',
                      borderRadius: 4,
                      background:
                        r.status === 'failed'
                          ? 'rgba(220,38,38,0.8)'
                          : r.status === 'queued'
                            ? 'rgba(22,163,74,0.8)'
                            : 'rgba(59,130,246,0.85)',
                    }}
                  />
                </div>
                {r.status === 'failed' && (r.reasonCode || r.reasonMessage) && (
                  <div style={{ fontSize: '0.75rem', color: '#b91c1c', marginTop: 2 }}>
                    {String(r.reasonCode || 'SECURITY_REJECTED')} - {String(r.reasonMessage || 'Blocked by security validation')}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <button className="btn-secondary mt-2 me-2" onClick={onParseInvoices} disabled={loading}>
          Parse PDF(s)
        </button>
      </div>
      {sessionDataBundle && (
        <>
          <h6 className="mb-2" style={{ color: textPrimary }}>
            Utility invoices
          </h6>
          <SessionDataTabs
            bundle={sessionDataBundle}
            textPrimary={textPrimary}
            textMuted={textMuted}
            canDelete={canDelete}
            loading={loading}
            onDeleteRow={handleTabDelete}
            onGenerateLineItemInvoice={onGenerateLineItemPdf}
            onUtilityUnfreeze={onUtilityUnfreeze}
            onUtilitySave={onUtilitySave}
            onUtilityPass={onUtilityPass}
            onFreezeAllUtilityRows={onFreezeAllUtilityRows}
            billingLinesFrozen={billingLinesFrozen}
            onUnfreezeBillingLineRow={canUnfreezeBillingLines ? onUnfreezeBillingLineRow : undefined}
            singleTabId="utility"
          />
          <h6 className="mb-2 mt-4" style={{ color: textPrimary }}>
            Parsed invoices
          </h6>
          <p className="small hint-text mb-2">
            Rows are sorted by parse start time (newest first). Timestamps use your browser timezone.
          </p>
          <SessionDataTabs
            bundle={sessionDataBundle}
            textPrimary={textPrimary}
            textMuted={textMuted}
            canDelete={canDelete}
            loading={loading}
            onDeleteRow={handleTabDelete}
            onGenerateLineItemInvoice={onGenerateLineItemPdf}
            onUtilityUnfreeze={onUtilityUnfreeze}
            onUtilitySave={onUtilitySave}
            onUtilityPass={onUtilityPass}
            onFreezeAllUtilityRows={onFreezeAllUtilityRows}
            billingLinesFrozen={billingLinesFrozen}
            onUnfreezeBillingLineRow={canUnfreezeBillingLines ? onUnfreezeBillingLineRow : undefined}
            singleTabId="parsed"
            parsedSortByParseStarted
            parsedTimestampColumns={Array.from(PARSED_LOCAL_TS_COLUMNS)}
            onRefreshParsedData={() => {
              if (!selectedSessionId) return;
              void refreshSessionDetail(selectedSessionId);
            }}
          />
        </>
      )}
    </>
  );
}
