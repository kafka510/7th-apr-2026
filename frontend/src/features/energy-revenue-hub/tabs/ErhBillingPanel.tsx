import { SessionDataTabs, type SessionDetailBundle, type TabId } from '../SessionDataTabs';

type Props = {
  textPrimary: string;
  textMuted: string;
  loading: boolean;
  selectedSessionId: string;
  sessionDataBundle: SessionDetailBundle;
  coverageSummary: Record<string, unknown>;
  pendingAssets: Array<Record<string, unknown>>;
  conflicts: Array<Record<string, unknown>>;
  onGenerateTable: () => Promise<void>;
  onRecalculateLines: () => Promise<void>;
  canUnfreezeBillingLines: boolean;
  onUnfreezeBillingLines: () => Promise<void>;
  onTestSharepointConnection: () => void;
  sharepointTestResult: string;
  canDelete: boolean;
  sessionAddAssetCode: string;
  setSessionAddAssetCode: (s: string) => void;
  onAddAssetToSession: () => Promise<void>;
  billingLinesFrozen: boolean;
  handleTabDelete: (tab: TabId, row: Record<string, unknown>) => Promise<void>;
  onGenerateLineItemPdf: (row: Record<string, unknown>) => Promise<void>;
  onUtilityUnfreeze: (row: Record<string, unknown>) => Promise<void>;
  onUtilitySave: (row: Record<string, unknown>, payload: Record<string, unknown>) => Promise<void>;
  onUtilityPass: (row: Record<string, unknown>) => Promise<void>;
  onFreezeAllUtilityRows: () => Promise<void>;
  onUnfreezeBillingLineRow: (row: Record<string, unknown>) => Promise<void>;
  onUnfreezeBillingLineGroup?: (groupKey: string) => Promise<void>;
  refreshSessionDetail: (id: string) => Promise<void>;
  sessionDetail: any;
  newUtilityInvoiceNo: string;
  setNewUtilityInvoiceNo: (s: string) => void;
  newUtilityTotalAmount: string;
  setNewUtilityTotalAmount: (s: string) => void;
  newPaymentInvoiceId: string;
  setNewPaymentInvoiceId: (s: string) => void;
  newPaymentAmount: string;
  setNewPaymentAmount: (s: string) => void;
  newReadingDeviceId: string;
  setNewReadingDeviceId: (s: string) => void;
  newReadingValue: string;
  setNewReadingValue: (s: string) => void;
  newAssetGenMonth: string;
  setNewAssetGenMonth: (s: string) => void;
  newAssetGenKwh: string;
  setNewAssetGenKwh: (s: string) => void;
  newPenaltyType: string;
  setNewPenaltyType: (s: string) => void;
  newPenaltyAmount: string;
  setNewPenaltyAmount: (s: string) => void;
  newAdjustmentType: string;
  setNewAdjustmentType: (s: string) => void;
  newAdjustmentAmount: string;
  setNewAdjustmentAmount: (s: string) => void;
  onCreateUtilityInvoice: () => Promise<void>;
  onCreatePayment: () => Promise<void>;
  onCreateMeterReading: () => Promise<void>;
  onCreateAssetGeneration: () => Promise<void>;
  onCreatePenalty: () => Promise<void>;
  onCreateAdjustment: () => Promise<void>;
};

export function ErhBillingPanel(props: Props) {
  const {
    textPrimary,
    textMuted,
    loading,
    selectedSessionId,
    sessionDataBundle,
    coverageSummary,
    pendingAssets,
    conflicts,
    onGenerateTable,
    onRecalculateLines,
    canUnfreezeBillingLines,
    onUnfreezeBillingLines,
    onTestSharepointConnection,
    sharepointTestResult,
    canDelete,
    sessionAddAssetCode,
    setSessionAddAssetCode,
    onAddAssetToSession,
    billingLinesFrozen,
    handleTabDelete,
    onGenerateLineItemPdf,
    onUtilityUnfreeze,
    onUtilitySave,
    onUtilityPass,
    onFreezeAllUtilityRows,
    onUnfreezeBillingLineRow,
    onUnfreezeBillingLineGroup,
    refreshSessionDetail,
    sessionDetail,
    newUtilityInvoiceNo,
    setNewUtilityInvoiceNo,
    newUtilityTotalAmount,
    setNewUtilityTotalAmount,
    newPaymentInvoiceId,
    setNewPaymentInvoiceId,
    newPaymentAmount,
    setNewPaymentAmount,
    newReadingDeviceId,
    setNewReadingDeviceId,
    newReadingValue,
    setNewReadingValue,
    newAssetGenMonth,
    setNewAssetGenMonth,
    newAssetGenKwh,
    setNewAssetGenKwh,
    newPenaltyType,
    setNewPenaltyType,
    newPenaltyAmount,
    setNewPenaltyAmount,
    newAdjustmentType,
    setNewAdjustmentType,
    newAdjustmentAmount,
    setNewAdjustmentAmount,
    onCreateUtilityInvoice,
    onCreatePayment,
    onCreateMeterReading,
    onCreateAssetGeneration,
    onCreatePenalty,
    onCreateAdjustment,
  } = props;

  return (
    <>
      <div className="mb-3 p-2 rounded" style={{ border: '1px solid rgba(148,163,184,0.3)', background: 'rgba(2,6,23,0.03)' }}>
        <div className="d-flex flex-wrap gap-3 hint-text">
          <span>
            Coverage expected: <strong>{String(coverageSummary.expected_utility_assets_count ?? 0)}</strong>
          </span>
          <span>
            Ready: <strong>{String(coverageSummary.ready_assets_count ?? 0)}</strong>
          </span>
          <span>
            Pending assets: <strong>{pendingAssets.length}</strong>
          </span>
          <span>
            Merge conflicts: <strong>{conflicts.length}</strong>
          </span>
        </div>
        <button
          type="button"
          className="btn btn-sm btn-primary mt-2 fw-semibold"
          style={{ boxShadow: '0 1px 2px rgba(0,0,0,0.2)' }}
          disabled={loading}
          onClick={() => selectedSessionId && void refreshSessionDetail(selectedSessionId)}
        >
          Refresh session data
        </button>
      </div>

      <div className="d-flex flex-wrap gap-2 mb-3">
        <button
          className="btn btn-primary fw-semibold"
          type="button"
          onClick={onGenerateTable}
          disabled={loading}
          style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
        >
          Generate billing table
        </button>
        <button
          className="btn btn-info text-dark fw-semibold"
          type="button"
          onClick={() => void onRecalculateLines()}
          disabled={loading}
          style={{ boxShadow: '0 2px 4px rgba(8, 145, 178, 0.3)' }}
        >
          Recalculate lines
        </button>
        {canUnfreezeBillingLines && selectedSessionId && (
          <button
            type="button"
            className="btn btn-warning text-dark fw-semibold"
            onClick={() => void onUnfreezeBillingLines()}
            disabled={loading}
            title="Clear frozen billing lines so Generate Billing Table can run again"
            style={{ boxShadow: '0 2px 4px rgba(217, 119, 6, 0.35)' }}
          >
            Unfreeze billing lines
          </button>
        )}
        <button
          className="btn btn-outline-secondary fw-semibold"
          type="button"
          onClick={onTestSharepointConnection}
          disabled={loading}
          style={{ borderWidth: 2 }}
        >
          Test SharePoint connection
        </button>
      </div>
      {sharepointTestResult && <div className="hint-text mb-3">Last test path: {sharepointTestResult}</div>}
      {canDelete && (
        <div className="mb-3" style={{ maxWidth: 520 }}>
          <label className="ui-label">Superuser: add asset to session</label>
          <div className="d-flex gap-2">
            <input
              type="text"
              className="ui-input"
              placeholder="asset_code"
              value={sessionAddAssetCode}
              onChange={(e) => setSessionAddAssetCode(e.target.value)}
            />
            <button
              type="button"
              className="btn btn-success fw-semibold"
              disabled={loading || !selectedSessionId}
              onClick={() => void onAddAssetToSession()}
              style={{ boxShadow: '0 2px 4px rgba(22, 163, 74, 0.35)' }}
            >
              Add
            </button>
          </div>
        </div>
      )}
      <h6 className="mb-2" style={{ color: textPrimary }}>
        Billing line items
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
        onUnfreezeBillingLineGroup={canUnfreezeBillingLines ? onUnfreezeBillingLineGroup : undefined}
        singleTabId="lines"
      />

      <div className="mt-4">
        <h6 className="mb-2" style={{ color: textPrimary }}>
          Add records
        </h6>
        <p className="small mb-2" style={{ color: textMuted }}>
          View and delete rows in the tabs above (25 per page). Superusers see Delete where supported.
          {billingLinesFrozen ? <> Frozen billing lines: delete is hidden on the Billing line items tab until unfreeze.</> : null}
        </p>
        <div className="mb-2" style={{ color: textMuted }}>
          <strong>Utility invoice</strong>
        </div>
        <div className="d-flex gap-2 mb-3 flex-wrap">
          <input
            className="ui-input"
            placeholder="Invoice number"
            value={newUtilityInvoiceNo}
            onChange={(e) => setNewUtilityInvoiceNo(e.target.value)}
          />
          <input
            className="ui-input"
            placeholder="Total amount"
            value={newUtilityTotalAmount}
            onChange={(e) => setNewUtilityTotalAmount(e.target.value)}
          />
          <button
            className="btn btn-primary fw-semibold"
            type="button"
            onClick={onCreateUtilityInvoice}
            disabled={loading}
            style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
          >
            Add Utility Invoice
          </button>
        </div>

        <div className="mb-2" style={{ color: textMuted }}>
          <strong>Payment</strong>
        </div>
        <div className="d-flex gap-2 mb-3 flex-wrap">
          <select className="ui-select" value={newPaymentInvoiceId} onChange={(e) => setNewPaymentInvoiceId(e.target.value)}>
            <option value="">Select utility invoice</option>
            {(sessionDetail?.utility_invoices || []).map((u: any) => (
              <option key={u.id} value={u.id}>
                {u.invoice_number || u.id}
              </option>
            ))}
          </select>
          <input
            className="ui-input"
            placeholder="Payment amount"
            value={newPaymentAmount}
            onChange={(e) => setNewPaymentAmount(e.target.value)}
          />
          <button
            className="btn btn-primary fw-semibold"
            type="button"
            onClick={onCreatePayment}
            disabled={loading || !newPaymentInvoiceId}
            style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
          >
            Add Payment
          </button>
        </div>

        <div className="mb-2" style={{ color: textMuted }}>
          <strong>Meter reading</strong>
        </div>
        <div className="d-flex gap-2 mb-3 flex-wrap">
          <input
            className="ui-input"
            placeholder="Device ID (billing meter)"
            value={newReadingDeviceId}
            onChange={(e) => setNewReadingDeviceId(e.target.value)}
          />
          <input
            className="ui-input"
            placeholder="Cumulative value"
            value={newReadingValue}
            onChange={(e) => setNewReadingValue(e.target.value)}
          />
          <button
            className="btn btn-primary fw-semibold"
            type="button"
            onClick={onCreateMeterReading}
            disabled={loading || !newReadingDeviceId || !newReadingValue}
            style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
          >
            Add Reading
          </button>
        </div>

        <div className="mb-2" style={{ color: textMuted }}>
          <strong>Asset generation</strong>
        </div>
        <div className="d-flex gap-2 mb-3 flex-wrap">
          <input className="ui-input" placeholder="YYYY-MM" value={newAssetGenMonth} onChange={(e) => setNewAssetGenMonth(e.target.value)} />
          <input className="ui-input" placeholder="PV kWh" value={newAssetGenKwh} onChange={(e) => setNewAssetGenKwh(e.target.value)} />
          <button
            className="btn btn-primary fw-semibold"
            type="button"
            onClick={onCreateAssetGeneration}
            disabled={loading || !newAssetGenMonth}
            style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
          >
            Add Generation
          </button>
        </div>

        <div className="mb-2" style={{ color: textMuted }}>
          <strong>Penalty</strong>
        </div>
        <div className="d-flex gap-2 mb-3 flex-wrap">
          <input className="ui-input" placeholder="Penalty type" value={newPenaltyType} onChange={(e) => setNewPenaltyType(e.target.value)} />
          <input className="ui-input" placeholder="Penalty amount" value={newPenaltyAmount} onChange={(e) => setNewPenaltyAmount(e.target.value)} />
          <button
            className="btn btn-primary fw-semibold"
            type="button"
            onClick={onCreatePenalty}
            disabled={loading || !newPenaltyType}
            style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
          >
            Add Penalty
          </button>
        </div>

        <div className="mb-2" style={{ color: textMuted }}>
          <strong>Adjustment</strong>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <input className="ui-input" placeholder="Adjustment type" value={newAdjustmentType} onChange={(e) => setNewAdjustmentType(e.target.value)} />
          <input className="ui-input" placeholder="Adjustment amount" value={newAdjustmentAmount} onChange={(e) => setNewAdjustmentAmount(e.target.value)} />
          <button
            className="btn btn-primary fw-semibold"
            type="button"
            onClick={onCreateAdjustment}
            disabled={loading || !newAdjustmentType}
            style={{ boxShadow: '0 2px 4px rgba(37, 99, 235, 0.35)' }}
          >
            Add Adjustment
          </button>
        </div>
      </div>
    </>
  );
}
