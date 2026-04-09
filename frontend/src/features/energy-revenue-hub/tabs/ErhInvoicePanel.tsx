import type { Dispatch, SetStateAction } from 'react';
import { SessionDataTabs, type SessionDetailBundle, type TabId } from '../SessionDataTabs';
import { showInvoiceBlockersDialog } from '../erhInvoiceDialogs';
import type { BillingSession } from '../api';

type Props = {
  textPrimary: string;
  textMuted: string;
  loading: boolean;
  selectedSession: BillingSession | null;
  sessionDetail: any;
  sessionDataBundle: SessionDetailBundle;
  invoiceGenerationBlocked: boolean;
  invoiceHardBlockers: Array<Record<string, unknown>>;
  generationBlockers: Array<Record<string, unknown>>;
  selectedGeneratedIds: string[];
  setSelectedGeneratedIds: Dispatch<SetStateAction<string[]>>;
  generatedDownloadProgress: {
    active: boolean;
    total: number;
    completed: number;
    ok: number;
    failed: number;
    mode: 'zip' | 'files';
  };
  downloadGeneratedInvoices: (ids: string[]) => Promise<void>;
  onGenerateInvoice: () => Promise<void>;
  onPostInvoice: () => Promise<void>;
  canDelete: boolean;
  billingLinesFrozen: boolean;
  handleTabDelete: (tab: TabId, row: Record<string, unknown>) => Promise<void>;
  onGenerateLineItemPdf: (row: Record<string, unknown>) => Promise<void>;
  onUtilityUnfreeze: (row: Record<string, unknown>) => Promise<void>;
  onUtilitySave: (row: Record<string, unknown>, payload: Record<string, unknown>) => Promise<void>;
  onUtilityPass: (row: Record<string, unknown>) => Promise<void>;
  onFreezeAllUtilityRows: () => Promise<void>;
  canUnfreezeBillingLines: boolean;
  onUnfreezeBillingLineRow: (row: Record<string, unknown>) => Promise<void>;
};

export function ErhInvoicePanel(props: Props) {
  const {
    textPrimary,
    textMuted,
    loading,
    selectedSession,
    sessionDetail,
    sessionDataBundle,
    invoiceGenerationBlocked,
    invoiceHardBlockers,
    generationBlockers,
    selectedGeneratedIds,
    setSelectedGeneratedIds,
    generatedDownloadProgress,
    downloadGeneratedInvoices,
    onGenerateInvoice,
    onPostInvoice,
    canDelete,
    billingLinesFrozen,
    handleTabDelete,
    onGenerateLineItemPdf,
    onUtilityUnfreeze,
    onUtilitySave,
    onUtilityPass,
    onFreezeAllUtilityRows,
    canUnfreezeBillingLines,
    onUnfreezeBillingLineRow,
  } = props;

  return (
    <>
      {Array.isArray(sessionDetail?.generated_invoices) && sessionDetail.generated_invoices.length > 0 ? (
        <div className="mb-3 p-2 rounded" style={{ border: '1px solid rgba(148,163,184,0.3)', background: 'rgba(2,6,23,0.03)' }}>
          <div className="d-flex justify-content-between align-items-center gap-2 flex-wrap">
            <div className="hint-text">
              Generated invoices available: <strong>{sessionDetail.generated_invoices.length}</strong>
            </div>
            <div className="d-flex gap-2 flex-wrap">
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={loading || selectedGeneratedIds.length === 0}
                onClick={() => void downloadGeneratedInvoices(selectedGeneratedIds)}
              >
                Download selected
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={loading || sessionDetail.generated_invoices.length === 0}
                onClick={() =>
                  void downloadGeneratedInvoices(
                    (sessionDetail.generated_invoices as Array<Record<string, unknown>>)
                      .map((r) => String(r.id || '').trim())
                      .filter(Boolean)
                  )
                }
              >
                Download all
              </button>
            </div>
          </div>
          <div className="mt-2" style={{ maxHeight: 150, overflowY: 'auto', fontSize: '0.82rem', color: textMuted }}>
            {generatedDownloadProgress.total > 0 && (
              <div className="mb-2">
                Download progress ({generatedDownloadProgress.mode === 'zip' ? 'ZIP' : 'Files'}):{' '}
                <strong>
                  {generatedDownloadProgress.completed}/{generatedDownloadProgress.total}
                </strong>{' '}
                ({Math.round((generatedDownloadProgress.completed / Math.max(1, generatedDownloadProgress.total)) * 100)}%) | ok:{' '}
                <strong>{generatedDownloadProgress.ok}</strong> | failed: <strong>{generatedDownloadProgress.failed}</strong>
                {generatedDownloadProgress.active ? ' ...downloading' : ''}
              </div>
            )}
            {(sessionDetail.generated_invoices as Array<Record<string, unknown>>).map((r, i) => {
              const id = String(r.id || '').trim();
              const label = String(r.file_path || `generated_invoice_${i + 1}`);
              const checked = selectedGeneratedIds.includes(id);
              return (
                <label key={id || `g-${i}`} className="d-flex align-items-center gap-2 mb-1">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      if (!id) return;
                      setSelectedGeneratedIds((prev) =>
                        e.target.checked ? Array.from(new Set([...prev, id])) : prev.filter((x) => x !== id)
                      );
                    }}
                  />
                  <span>{label}</span>
                </label>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="d-flex flex-wrap gap-2 mb-3">
        <button className="btn-primary" onClick={onGenerateInvoice} disabled={loading || invoiceGenerationBlocked}>
          Generate invoice PDF
        </button>
        {invoiceGenerationBlocked && (
          <span className="align-self-center d-inline-flex flex-wrap align-items-center gap-2 hint-text" style={{ color: '#f59e0b' }}>
            <span>
              Blocked:{' '}
              {(invoiceHardBlockers.length ? invoiceHardBlockers : generationBlockers)
                .map((b) => String(b.message || b.code || 'Issue'))
                .join(' | ')}
            </span>
            <button
              type="button"
              className="btn btn-sm btn-outline-warning"
              onClick={() =>
                void showInvoiceBlockersDialog(
                  invoiceHardBlockers.length ? invoiceHardBlockers : generationBlockers,
                  'Invoice generation blocked'
                )
              }
            >
              View details
            </button>
          </span>
        )}
        {generationBlockers.length > 0 && !invoiceGenerationBlocked && (
          <span className="align-self-center hint-text" style={{ color: textMuted }}>
            Warnings present; generation allowed for ready assets.
          </span>
        )}
        <button
          className="btn-secondary"
          type="button"
          onClick={() => void onPostInvoice()}
          disabled={loading || selectedSession?.status !== 'GENERATED'}
          title={selectedSession?.status !== 'GENERATED' ? 'Generate invoice first' : 'Mark session as POSTED'}
        >
          Post invoice
        </button>
      </div>
      <h6 className="mb-2" style={{ color: textPrimary }}>
        Generated invoice files
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
        singleTabId="generated"
      />
    </>
  );
}
