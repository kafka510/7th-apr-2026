 
import { useState } from 'react';
import { downloadUserActivity } from '../api';
import type { DownloadActivityFilters } from '../types';

export function DownloadSection() {
  const [filters, setFilters] = useState<DownloadActivityFilters>({
    start_date: '',
    end_date: '',
    user: '',
    action: '',
    ip: '',
    include_suspicious: false,
  });
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [showUrl, setShowUrl] = useState(false);

  const handleDownload = async () => {
    try {
      setLoading(true);
      await downloadUserActivity(filters);
    } catch (error) {
      console.error('Error downloading activity:', error);
      alert('Failed to download activity data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const generateDownloadUrl = () => {
    const queryParams = new URLSearchParams();
    if (filters.start_date) queryParams.append('start_date', filters.start_date);
    if (filters.end_date) queryParams.append('end_date', filters.end_date);
    if (filters.user) queryParams.append('user', filters.user);
    if (filters.action) queryParams.append('action', filters.action);
    if (filters.ip) queryParams.append('ip', filters.ip);
    if (filters.include_suspicious) queryParams.append('include_suspicious', 'true');

    const url = `/download-user-activity/?${queryParams.toString()}`;
    setDownloadUrl(url);
    setShowUrl(true);
  };

  const copyUrl = () => {
    if (downloadUrl) {
      navigator.clipboard.writeText(window.location.origin + downloadUrl);
      alert('Download URL copied to clipboard!');
    }
  };

  return (
    <div className="bg-light my-4 rounded p-3">
      <h4 className="mb-3">Download Activity Data (Admin Only)</h4>
      <div className="alert alert-info alert-dismissible fade show" role="alert">
        <i className="fas fa-info-circle"></i>
        <strong>Comprehensive Download:</strong> Downloads ALL user activity for today (current date in IST) with
        complete details including:
        <br />
        <small>
          • User information (ID, username, email) • Request details (IP, user agent, method, status) • Performance
          metrics (response time, size) • Security analysis (risk level, flags) • Geolocation data (country, city,
          region) • Request parameters (GET/POST data)
        </small>
        <br />
        Use filters below to customize the date range and other criteria. Click &quot;Download CSV&quot; for instant
        download, or &quot;Get Download Link&quot; if automatic download doesn&apos;t work.
      </div>
      <div className="row g-3">
        <div className="col-md-2">
          <label htmlFor="start_date" className="form-label">
            Start Date
          </label>
          <input
            type="date"
            className="form-control"
            id="start_date"
            value={filters.start_date || ''}
            onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
            placeholder="Leave empty for today"
          />
          <small className="text-muted">Default: Today</small>
        </div>
        <div className="col-md-2">
          <label htmlFor="end_date" className="form-label">
            End Date
          </label>
          <input
            type="date"
            className="form-control"
            id="end_date"
            value={filters.end_date || ''}
            onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
            placeholder="Leave empty for today"
          />
          <small className="text-muted">Default: Today</small>
        </div>
        <div className="col-md-2">
          <label htmlFor="user_filter" className="form-label">
            User
          </label>
          <input
            type="text"
            className="form-control"
            id="user_filter"
            value={filters.user || ''}
            onChange={(e) => setFilters({ ...filters, user: e.target.value })}
            placeholder="Username"
          />
        </div>
        <div className="col-md-2">
          <label htmlFor="action_filter" className="form-label">
            Action
          </label>
          <select
            className="form-select"
            id="action_filter"
            value={filters.action || ''}
            onChange={(e) => setFilters({ ...filters, action: e.target.value })}
          >
            <option value="">All Actions</option>
            <option value="login">Login</option>
            <option value="logout">Logout</option>
            <option value="view">View</option>
            <option value="create">Create</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
            <option value="download">Download</option>
            <option value="upload">Upload</option>
          </select>
        </div>
        <div className="col-md-2">
          <label htmlFor="ip_filter" className="form-label">
            IP Address
          </label>
          <input
            type="text"
            className="form-control"
            id="ip_filter"
            value={filters.ip || ''}
            onChange={(e) => setFilters({ ...filters, ip: e.target.value })}
            placeholder="IP Address"
          />
        </div>
        <div className="col-md-2">
          <div className="form-check mt-4">
            <input
              className="form-check-input"
              type="checkbox"
              id="include_suspicious"
              checked={filters.include_suspicious || false}
              onChange={(e) => setFilters({ ...filters, include_suspicious: e.target.checked })}
            />
            <label className="form-check-label" htmlFor="include_suspicious">
              Suspicious Only
            </label>
          </div>
          <div className="btn-group-vertical d-grid mt-2 gap-2">
            <button
              type="button"
              className="btn btn-success btn-sm"
              onClick={handleDownload}
              disabled={loading}
            >
              <i className="fas fa-download"></i> {loading ? 'Downloading...' : 'Download CSV'}
            </button>
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={generateDownloadUrl}>
              <i className="fas fa-link"></i> Get Download Link
            </button>
          </div>
          {showUrl && downloadUrl && (
            <div className="mt-3">
              <div className="alert alert-success">
                <h6>
                  <i className="fas fa-download"></i> Your Download URL is Ready!
                </h6>
                <div className="input-group mb-2">
                  <input
                    type="text"
                    className="form-control"
                    value={window.location.origin + downloadUrl}
                    readOnly
                  />
                  <button className="btn btn-outline-secondary" type="button" onClick={copyUrl}>
                    <i className="fas fa-copy"></i> Copy
                  </button>
                </div>
                <a href={downloadUrl} className="btn btn-primary btn-sm" target="_blank" rel="noopener noreferrer">
                  <i className="fas fa-external-link-alt"></i> Open Download Link
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

