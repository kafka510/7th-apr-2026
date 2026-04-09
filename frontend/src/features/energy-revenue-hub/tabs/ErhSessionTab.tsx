import type { BillingSession, EligibleBillingAsset } from '../api';

type Props = {
  country: string;
  setCountry: (v: string) => void;
  countryOptions: string[];
  createContractType: string;
  setCreateContractType: (v: string) => void;
  registeredContractKeys: string[];
  createBillingMonth: string;
  setCreateBillingMonth: (v: string) => void;
  portfolio: string;
  setPortfolio: (v: string) => void;
  portfolioOptions: string[];
  assetSearch: string;
  setAssetSearch: (v: string) => void;
  eligibleAssetsFiltered: EligibleBillingAsset[];
  startDate: string;
  setStartDate: (v: string) => void;
  endDate: string;
  setEndDate: (v: string) => void;
  onCreateSession: () => void | Promise<void>;
  loading: boolean;
  contractTypeFilter: string;
  setContractTypeFilter: (v: string) => void;
  billingMonthFilter: string;
  setBillingMonthFilter: (v: string) => void;
  refreshSessions: (showSpinner?: boolean) => void | Promise<void>;
  sessionSearch: string;
  setSessionSearch: (v: string) => void;
  filteredSessions: BillingSession[];
  sessionsLength: number;
  selectedSessionId: string;
  setSelectedSessionId: (v: string) => void;
  sessionIdLookup: string;
  setSessionIdLookup: (v: string) => void;
  onSelectSessionById: () => void | Promise<void>;
};

export function ErhSessionTab(props: Props) {
  const {
    country,
    setCountry,
    countryOptions,
    createContractType,
    setCreateContractType,
    registeredContractKeys,
    createBillingMonth,
    setCreateBillingMonth,
    portfolio,
    setPortfolio,
    portfolioOptions,
    assetSearch,
    setAssetSearch,
    eligibleAssetsFiltered,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    onCreateSession,
    loading,
    contractTypeFilter,
    setContractTypeFilter,
    billingMonthFilter,
    setBillingMonthFilter,
    refreshSessions,
    sessionSearch,
    setSessionSearch,
    filteredSessions,
    sessionsLength,
    selectedSessionId,
    setSelectedSessionId,
    sessionIdLookup,
    setSessionIdLookup,
    onSelectSessionById,
  } = props;

  return (
    <div className="col-12 col-xl-7">
      <div className="section-card">
        <div className="section-card-header">
          <h6 className="section-title mb-0">Create Billing Session</h6>
        </div>
        <div className="card-body px-0 pb-0">
          <div className="mb-2">
            <label className="ui-label">Country</label>
            <select className="ui-select" value={country} onChange={(e) => setCountry(e.target.value)}>
              {countryOptions.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="mb-2">
            <label className="ui-label">Contract profile (registered)</label>
            <select
              className="ui-select"
              value={createContractType}
              onChange={(e) => setCreateContractType(e.target.value)}
              disabled={!registeredContractKeys.length}
            >
              {registeredContractKeys.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
            {!registeredContractKeys.length ? (
              <div className="hint-text mt-1">Loading registered contract profiles…</div>
            ) : (
              <div className="hint-text mt-1">Must match a registered profile key (normalized like in the database).</div>
            )}
          </div>
          <div className="mb-2">
            <label className="ui-label">Billing month</label>
            <input
              type="month"
              className="ui-input"
              value={createBillingMonth}
              onChange={(e) => setCreateBillingMonth(e.target.value)}
            />
            <div className="hint-text mt-1">
              Lists assets with this contract type and country (and contract dates overlapping the month).
            </div>
          </div>
          <div className="mb-2">
            <label className="ui-label">Portfolio (optional override)</label>
            <select className="ui-select" value={portfolio} onChange={(e) => setPortfolio(e.target.value)} disabled={!country}>
              <option value="">Auto from asset list</option>
              {portfolioOptions.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="mb-2">
            <label className="ui-label">Eligible assets preview (read-only)</label>
            <input
              className="ui-input mb-2"
              placeholder="Search eligible assets..."
              value={assetSearch}
              onChange={(e) => setAssetSearch(e.target.value)}
            />
            <div className="hint-text">
              {eligibleAssetsFiltered.length} eligible asset(s) match the selected filters. Session scope is derived automatically.
            </div>
            <div className="mt-2" style={{ maxHeight: 140, overflowY: 'auto', border: '1px solid rgba(148,163,184,0.25)', borderRadius: 8 }}>
              {eligibleAssetsFiltered.slice(0, 50).map((a) => (
                <div key={a.asset_code} className="px-2 py-1" style={{ borderBottom: '1px solid rgba(148,163,184,0.12)' }}>
                  <span style={{ fontWeight: 600 }}>{a.asset_code}</span> <span className="hint-text">— {a.asset_name}</span>
                </div>
              ))}
              {eligibleAssetsFiltered.length === 0 && <div className="px-2 py-2 hint-text">No eligible assets found for these filters.</div>}
              {eligibleAssetsFiltered.length > 50 && (
                <div className="px-2 py-2 hint-text">Showing first 50. Narrow search to see others.</div>
              )}
            </div>
          </div>
          <div className="row g-2 mb-3">
            <div className="col">
              <label className="ui-label">Start Date (optional)</label>
              <input type="date" className="ui-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="col">
              <label className="ui-label">End Date (optional)</label>
              <input type="date" className="ui-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
            <div className="col-12 hint-text">
              Leave dates blank to use the full calendar month of <strong>{createBillingMonth || '—'}</strong>.
            </div>
          </div>
          <button className="btn-primary" onClick={onCreateSession} disabled={loading}>
            Create Session
          </button>
          <div className="hint-text mt-2">
            Assets are derived automatically from <code>assets_contracts</code> for the selected country, contract type, and billing month.
          </div>
        </div>
      </div>

      <div className="section-card mt-3">
        <div className="section-card-header">
          <h6 className="section-title mb-0">Select billing session</h6>
        </div>
        <div className="card-body px-0 pb-0">
          <div className="workflow-actions-sticky mb-2">
            <div className="mb-2">
              <label className="ui-label">Filter sessions (server)</label>
              <div className="row g-2">
                <div className="col-md-4">
                  <select className="ui-select" value={contractTypeFilter} onChange={(e) => setContractTypeFilter(e.target.value)}>
                    <option value="">All contract types</option>
                    {registeredContractKeys.map((k) => (
                      <option key={k} value={k}>
                        {k}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-4">
                  <input
                    type="month"
                    className="ui-input"
                    value={billingMonthFilter}
                    onChange={(e) => setBillingMonthFilter(e.target.value)}
                  />
                </div>
                <div className="col-md-4 d-flex align-items-end">
                  <button type="button" className="btn-secondary w-100" onClick={() => void refreshSessions(true)} disabled={loading}>
                    Apply filters
                  </button>
                </div>
              </div>
              <label className="ui-label mt-2">Find Session (client search)</label>
              <input
                type="text"
                className="ui-input"
                placeholder="Search id/country/portfolio/status/label/month"
                value={sessionSearch}
                onChange={(e) => setSessionSearch(e.target.value)}
              />
              <div className="hint-text mt-1">
                {filteredSessions.length} of {sessionsLength} session(s)
              </div>
            </div>
            <div className="mb-2">
              <label className="ui-label">Selected Session</label>
              <select className="ui-select" value={selectedSessionId} onChange={(e) => setSelectedSessionId(e.target.value)}>
                <option value="">Select session...</option>
                {filteredSessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.session_label || `${s.id.slice(0, 8)} | ${s.country}`} | {s.billing_month || '-'} | {s.billing_contract_type || '-'} |{' '}
                    {s.status}
                  </option>
                ))}
              </select>
              <div className="d-flex gap-2 mt-2">
                <input
                  type="text"
                  className="ui-input"
                  placeholder="Paste full session id"
                  value={sessionIdLookup}
                  onChange={(e) => setSessionIdLookup(e.target.value)}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void onSelectSessionById()}
                  disabled={loading || !sessionIdLookup.trim()}
                >
                  Load
                </button>
              </div>
              <button type="button" className="btn-secondary mt-2" onClick={() => void refreshSessions(true)} disabled={loading}>
                Refresh sessions
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
