import { SessionDataTabs, type SessionDetailBundle, type TabId } from '../SessionDataTabs';
import { AUDIT_SUB_TABS } from '../erhTypes';

type Props = {
  sessionDataBundle: SessionDetailBundle;
  textPrimary: string;
  textMuted: string;
  canDelete: boolean;
  loading: boolean;
  handleTabDelete: (tab: TabId, row: Record<string, unknown>) => Promise<void>;
  onGenerateLineItemPdf: (row: Record<string, unknown>) => Promise<void>;
  onUtilityUnfreeze: (row: Record<string, unknown>) => Promise<void>;
  onUtilitySave: (row: Record<string, unknown>, payload: Record<string, unknown>) => Promise<void>;
  onUtilityPass: (row: Record<string, unknown>) => Promise<void>;
  onFreezeAllUtilityRows: () => Promise<void>;
  billingLinesFrozen: boolean;
  canUnfreezeBillingLines: boolean;
  onUnfreezeBillingLineRow: (row: Record<string, unknown>) => Promise<void>;
};

export function ErhAuditPanel(props: Props) {
  const {
    sessionDataBundle,
    textPrimary,
    textMuted,
    canDelete,
    loading,
    handleTabDelete,
    onGenerateLineItemPdf,
    onUtilityUnfreeze,
    onUtilitySave,
    onUtilityPass,
    onFreezeAllUtilityRows,
    billingLinesFrozen,
    canUnfreezeBillingLines,
    onUnfreezeBillingLineRow,
  } = props;

  return (
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
      visibleTabIds={AUDIT_SUB_TABS}
    />
  );
}
