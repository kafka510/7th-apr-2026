import type { ReactNode } from 'react';
import type { BillingSession } from '../api';
import type { ErhPageTab } from '../erhTypes';
import { erhWorkspaceTitle } from '../erhTypes';

type Props = {
  pageTab: ErhPageTab;
  textMuted: string;
  selectedSessionId: string;
  selectedSession: BillingSession | null;
  sessionDetail: unknown;
  children: ReactNode;
};

export function ErhWorkspace(props: Props) {
  const { pageTab, textMuted, selectedSessionId, selectedSession, sessionDetail, children } = props;

  return (
    <div className="col-12">
      <div className="section-card">
        <div className="section-card-header">
          <h6 className="section-title mb-0">{erhWorkspaceTitle(pageTab)}</h6>
        </div>
        <div className="card-body px-0 pb-0">
          {!selectedSessionId && (
            <p style={{ color: textMuted }} className="mb-0">
              Select or create a billing session on the <strong>Session</strong> tab to use this area.
            </p>
          )}
          {selectedSession && (
            <>
              <p className="mb-2">
                <strong>ID:</strong> {selectedSession.id}
                <br />
                <strong>Status:</strong> {selectedSession.status}
                <br />
                <strong>Range:</strong> {selectedSession.start_date || '-'} to {selectedSession.end_date || '-'}
                {(sessionDetail as { session?: { invoice_template_id?: string } } | null)?.session?.invoice_template_id ? (
                  <>
                    <br />
                    <strong>Invoice template:</strong>{' '}
                    {(sessionDetail as { session: { invoice_template_id: string } }).session.invoice_template_id}
                  </>
                ) : null}
              </p>
              {children}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
