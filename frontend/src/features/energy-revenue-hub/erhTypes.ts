import type { TabId } from './SessionDataTabs';

export type ErhPageTab = 'session' | 'parse' | 'billing' | 'invoice' | 'audit';

/** Section title for the workspace card (non-session tabs). */
export function erhWorkspaceTitle(tab: ErhPageTab): string {
  switch (tab) {
    case 'parse':
      return 'Parse';
    case 'billing':
      return 'Billing';
    case 'invoice':
      return 'Invoice';
    case 'audit':
      return 'Audit logs';
    default:
      return 'Workspace';
  }
}

export const AUDIT_SUB_TABS: TabId[] = ['payments', 'meters', 'generation', 'penalties', 'adjustments', 'audit'];

export const PARSED_LOCAL_TS_COLUMNS = ['parse_started_at', 'parse_completed_at', 'created_at'] as const;
