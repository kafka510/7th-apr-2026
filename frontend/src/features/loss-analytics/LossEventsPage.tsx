import { useEffect, useState } from 'react';
import type { LossEvent, LossEventFilters, LossEventLog } from './types';
import { fetchLossEvents, updateLossEventLegitimacy, fetchLossEventLogs } from './api';

export function LossEventsPage() {
  const [events, setEvents] = useState<LossEvent[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<LossEventFilters>({});

  const [logsOpen, setLogsOpen] = useState(false);
  const [logsEvent, setLogsEvent] = useState<LossEvent | null>(null);
  const [logs, setLogs] = useState<LossEventLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);

  const loadEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const pageData = await fetchLossEvents(filters, page, pageSize);
      setEvents(pageData.events);
      setTotal(pageData.total);
    } catch (e: any) {
      setError(e.message || 'Failed to load loss events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, filters.assetCode, filters.deviceId, filters.startTime, filters.endTime]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadEvents();
  };

  const handleConfirm = async (ev: LossEvent, value: boolean | null) => {
    try {
      await updateLossEventLegitimacy(ev.id, value);
      await loadEvents();
      if (logsOpen && logsEvent && logsEvent.id === ev.id) {
        // Refresh logs if modal is open for this event
        await handleShowLogs(ev);
      }
    } catch (e: any) {
      alert(e.message || 'Failed to update legitimacy');
    }
  };

  const handleShowLogs = async (ev: LossEvent) => {
    setLogsOpen(true);
    setLogsEvent(ev);
    setLogs([]);
    setLogsError(null);
    setLogsLoading(true);
    try {
      const data = await fetchLossEventLogs(ev.id);
      setLogs(data);
    } catch (e: any) {
      setLogsError(e.message || 'Failed to load logs');
    } finally {
      setLogsLoading(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="container-fluid py-3">
      <h4 className="mb-3">Loss Events</h4>

      <form className="row g-2 mb-3" onSubmit={handleFilterSubmit}>
        <div className="col-md-3">
          <label className="form-label">Asset code</label>
          <input
            type="text"
            className="form-control"
            value={filters.assetCode || ''}
            onChange={(e) => setFilters({ ...filters, assetCode: e.target.value || undefined })}
          />
        </div>
        <div className="col-md-3">
          <label className="form-label">Device ID</label>
          <input
            type="text"
            className="form-control"
            placeholder="Single device for now"
            value={filters.deviceId || ''}
            onChange={(e) => setFilters({ ...filters, deviceId: e.target.value || undefined })}
          />
        </div>
        <div className="col-md-3">
          <label className="form-label">Start time (ISO)</label>
          <input
            type="text"
            className="form-control"
            placeholder="2025-09-18T00:00:00+00:00"
            value={filters.startTime || ''}
            onChange={(e) => setFilters({ ...filters, startTime: e.target.value || undefined })}
          />
        </div>
        <div className="col-md-3">
          <label className="form-label">End time (ISO)</label>
          <input
            type="text"
            className="form-control"
            placeholder="2025-09-18T23:59:59+00:00"
            value={filters.endTime || ''}
            onChange={(e) => setFilters({ ...filters, endTime: e.target.value || undefined })}
          />
        </div>
        <div className="col-12 d-flex justify-content-end mt-2">
          <button type="submit" className="btn btn-primary btn-sm">
            Apply filters
          </button>
        </div>
      </form>

      {loading ? (
        <p>Loading events…</p>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : (
        <>
          <div className="table-responsive">
            <table className="table table-sm table-striped align-middle">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Asset</th>
                  <th>Device</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>State</th>
                  <th>Loss kWh</th>
                  <th>Legitimate?</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td>{ev.id}</td>
                    <td>{ev.asset_code}</td>
                    <td>{ev.device_id}</td>
                    <td>{ev.start_ts}</td>
                    <td>{ev.end_ts}</td>
                    <td>{ev.oem_state_label || ev.internal_state || '-'}</td>
                    <td>{ev.loss_kwh != null ? ev.loss_kwh.toFixed(3) : '-'}</td>
                    <td>
                      {ev.is_legitimate === true
                        ? 'Yes'
                        : ev.is_legitimate === false
                        ? 'No'
                        : 'Pending'}
                    </td>
                    <td>
                      <div className="btn-group btn-group-sm" role="group">
                        <button
                          type="button"
                          className="btn btn-outline-success"
                          onClick={() => handleConfirm(ev, true)}
                        >
                          Confirm
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={() => handleConfirm(ev, null)}
                        >
                          Pending
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-danger"
                          onClick={() => handleConfirm(ev, false)}
                        >
                          Reject
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-info"
                          onClick={() => handleShowLogs(ev)}
                        >
                          Logs
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {events.length === 0 && (
                  <tr>
                    <td colSpan={9} className="text-center">
                      No events found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="d-flex justify-content-between align-items-center mt-2">
            <div>
              Showing page {page} of {totalPages} ({total} total)
            </div>
            <div className="btn-group btn-group-sm">
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Prev
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {logsOpen && logsEvent && (
        <div
          className="modal d-block"
          tabIndex={-1}
          role="dialog"
          style={{ background: 'rgba(0,0,0,0.5)' }}
        >
          <div className="modal-dialog modal-lg" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Logs for event #{logsEvent.id}</h5>
                <button
                  type="button"
                  className="btn-close"
                  aria-label="Close"
                  onClick={() => setLogsOpen(false)}
                />
              </div>
              <div className="modal-body">
                {logsLoading ? (
                  <p>Loading logs…</p>
                ) : logsError ? (
                  <div className="alert alert-danger">{logsError}</div>
                ) : logs.length === 0 ? (
                  <p>No logs yet for this event.</p>
                ) : (
                  <ul className="list-group list-group-flush">
                    {logs.map((log) => (
                      <li key={log.id} className="list-group-item">
                        <div>
                          <strong>{log.created_at}</strong>{' '}
                          {log.username ? `by ${log.username}` : ''}
                        </div>
                        <div>
                          {String(log.old_value)} → {String(log.new_value)}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setLogsOpen(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

