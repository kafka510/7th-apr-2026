 
import { useState, useEffect } from 'react';
import { createUser } from '../api';
import type { Asset, CreateUserPayload } from '../types';

interface UserFormModalProps {
  show: boolean;
  onClose: () => void;
  onSuccess: () => void;
  assets: Asset[];
  countries: string[];
  portfolios: string[];
}

export function UserFormModal({
  show,
  onClose,
  onSuccess,
  assets,
  countries,
  portfolios,
}: UserFormModalProps) {
  const [formData, setFormData] = useState<CreateUserPayload>({
    username: '',
    email: '',
    password: '',
    role: '',
    access_control: [],
    countries: [],
    portfolios: [],
    sites: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectAllCountries, setSelectAllCountries] = useState(false);
  const [selectAllPortfolios, setSelectAllPortfolios] = useState(false);
  const [selectAllSites, setSelectAllSites] = useState(false);

  // Get unique sites from assets
  const sites = assets.map((asset) => asset.asset_code);

  useEffect(() => {
    if (!show) {
      // Reset form when modal closes
      setFormData({
        username: '',
        email: '',
        password: '',
        role: '',
        access_control: [],
        countries: [],
        portfolios: [],
        sites: [],
      });
      setError(null);
      setSelectAllCountries(false);
      setSelectAllPortfolios(false);
      setSelectAllSites(false);
    }
  }, [show]);

  const handleAccessControlChange = (value: string, checked: boolean) => {
    if (checked) {
      setFormData({
        ...formData,
        access_control: [...(Array.isArray(formData.access_control) ? formData.access_control : []), value],
      });
    } else {
      setFormData({
        ...formData,
        access_control: (Array.isArray(formData.access_control) ? formData.access_control : []).filter((v) => v !== value),
      });
    }
  };


  const handleSelectAllCountries = (checked: boolean) => {
    setSelectAllCountries(checked);
    if (checked) {
      setFormData({
        ...formData,
        countries: [...countries],
      });
    } else {
      setFormData({
        ...formData,
        countries: [],
      });
    }
  };

  const handleSelectAllPortfolios = (checked: boolean) => {
    setSelectAllPortfolios(checked);
    if (checked) {
      setFormData({
        ...formData,
        portfolios: [...portfolios],
      });
    } else {
      setFormData({
        ...formData,
        portfolios: [],
      });
    }
  };

  const handleSelectAllSites = (checked: boolean) => {
    setSelectAllSites(checked);
    setFormData({
      ...formData,
      sites: checked ? [...sites] : [],
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!formData.password.trim()) {
      setError('Password is required.');
      return;
    }
    setLoading(true);

    try {
      await createUser(formData);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  if (!show) return null;

  return (
    <div
      className="modal fade show"
      style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}
      tabIndex={-1}
    >
      <div className="modal-dialog modal-xl">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Create New User</h5>
            <button
              type="button"
              className="btn-close"
              onClick={onClose}
              aria-label="Close"
            ></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                </div>
              )}

              <div className="row mb-3">
                <div className="col-md-3">
                  <label htmlFor="username" className="form-label">
                    Username <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                  />
                </div>
                <div className="col-md-3">
                  <label htmlFor="email" className="form-label">
                    Email <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    className="form-control"
                    id="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>
                <div className="col-md-2">
                  <label htmlFor="password" className="form-label">
                    Password <span className="text-danger">*</span>
                  </label>
                  <input
                    type="password"
                    className="form-control"
                    id="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    autoComplete="new-password"
                    required
                  />
                </div>
                <div className="col-md-2">
                  <label htmlFor="role" className="form-label">
                    Role <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    id="role"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    required
                  >
                    <option value="">Select Role</option>
                    <option value="admin">Admin</option>
                    <option value="om">O&M</option>
                    <option value="customer">Customer</option>
                    <option value="management">Management</option>
                    <option value="others">Others</option>
                  </select>
                </div>
                <div className="col-md-2">
                  <label className="form-label">
                    <strong>App Access:</strong>
                  </label>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="web_access"
                      checked={(Array.isArray(formData.access_control) ? formData.access_control : []).includes('web_access')}
                      onChange={(e) => handleAccessControlChange('web_access', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="web_access">
                      Web Access
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ticketing_access"
                      checked={(Array.isArray(formData.access_control) ? formData.access_control : []).includes('ticketing_access')}
                      onChange={(e) => handleAccessControlChange('ticketing_access', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="ticketing_access">
                      Ticketing Access
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="api_access"
                      checked={(Array.isArray(formData.access_control) ? formData.access_control : []).includes('api_access')}
                      onChange={(e) => handleAccessControlChange('api_access', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="api_access">
                      API Access
                    </label>
                  </div>
                </div>
              </div>

              <div className="row mb-3">
                <div className="col-md-4">
                  <label htmlFor="countries" className="form-label">Countries</label>
                  <div className="form-check mb-2">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="select_all_countries"
                      checked={selectAllCountries}
                      onChange={(e) => handleSelectAllCountries(e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="select_all_countries">
                      Select All Countries
                    </label>
                  </div>
                  <select
                    className="form-select"
                    id="countries"
                    multiple
                    size={5}
                    value={formData.countries || []}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                      setFormData({ ...formData, countries: selected });
                    }}
                  >
                    {countries.map((country) => (
                      <option key={country} value={country}>
                        {country}
                      </option>
                    ))}
                  </select>
                  <small className="text-muted">Gives access to ALL sites in selected countries</small>
                </div>
                <div className="col-md-4">
                  <label htmlFor="portfolios" className="form-label">Portfolios</label>
                  <div className="form-check mb-2">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="select_all_portfolios"
                      checked={selectAllPortfolios}
                      onChange={(e) => handleSelectAllPortfolios(e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="select_all_portfolios">
                      Select All Portfolios
                    </label>
                  </div>
                  <select
                    className="form-select"
                    id="portfolios"
                    multiple
                    size={5}
                    value={formData.portfolios || []}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                      setFormData({ ...formData, portfolios: selected });
                    }}
                  >
                    {portfolios.map((portfolio) => (
                      <option key={portfolio} value={portfolio}>
                        {portfolio}
                      </option>
                    ))}
                  </select>
                  <small className="text-muted">Gives access to ALL sites in selected portfolios</small>
                </div>
                <div className="col-md-4">
                  <label htmlFor="sites" className="form-label">Sites</label>
                  <div className="form-check mb-2">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="select_all_sites"
                      checked={selectAllSites}
                      onChange={(e) => handleSelectAllSites(e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="select_all_sites">
                      Select All Sites
                    </label>
                  </div>
                  <select
                    className="form-select"
                    id="sites"
                    multiple
                    size={5}
                    value={formData.sites || []}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                      setFormData({ ...formData, sites: selected });
                    }}
                  >
                    {sites.map((site) => (
                      <option key={site} value={site}>
                        {assets.find((a) => a.asset_code === site)?.asset_name || site}
                      </option>
                    ))}
                  </select>
                  <small className="text-muted">
                    Gives access ONLY to selected sites (overrides country/portfolio access)
                  </small>
                </div>
              </div>

              <div className="alert alert-warning">
                <strong>Priority Order:</strong> Site Access &gt; Portfolio Access &gt; Country Access
                <br />
                If you select specific sites, country and portfolio access will be ignored.
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create User'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

