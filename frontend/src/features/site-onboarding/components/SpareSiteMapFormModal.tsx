import { useState, useEffect } from 'react';
import type { SpareSiteMap, SpareMaster, LocationMaster, AssetList } from '../types';
import { fetchSpareMaster, fetchLocationMaster, getAllAssets } from '../api';

interface SpareSiteMapFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<SpareSiteMap>) => void;
  mapping: SpareSiteMap | null;
}

export function SpareSiteMapFormModal({ isOpen, onClose, onSave, mapping }: SpareSiteMapFormModalProps) {
  const [formData, setFormData] = useState<Partial<SpareSiteMap>>({
    spare_id: undefined,
    asset_code: '',
    location_id: undefined,
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [spares, setSpares] = useState<SpareMaster[]>([]);
  const [locations, setLocations] = useState<LocationMaster[]>([]);
  const [assets, setAssets] = useState<AssetList[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (mapping) {
        // Edit mode
        setFormData({
          spare_id: mapping.spare_id,
          asset_code: mapping.asset_code,
          location_id: mapping.location_id,
          is_active: mapping.is_active,
        });
      } else {
        // Add mode
        setFormData({
          spare_id: undefined,
          asset_code: '',
          location_id: undefined,
          is_active: true,
        });
      }

      // Load spares, locations, and assets
      setLoading(true);
      Promise.all([
        fetchSpareMaster(1, 1000, '').then(res => setSpares(res.data)),
        fetchLocationMaster(1, 1000, '').then(res => setLocations(res.data)),
        getAllAssets().then(setAssets),
      ]).finally(() => setLoading(false));
    }
  }, [isOpen, mapping]);

  useEffect(() => {
    if (isOpen) {
      const modalElement = document.getElementById('spareSiteMapModal');
      if (modalElement) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const modal = new (window as any).bootstrap.Modal(modalElement);
        modal.show();

        const handleHidden = () => {
          onClose();
        };
        modalElement.addEventListener('hidden.bs.modal', handleHidden);

        return () => {
          modalElement.removeEventListener('hidden.bs.modal', handleHidden);
          modal.dispose();
        };
      }
    }
  }, [isOpen, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.spare_id || !formData.asset_code || !formData.location_id) {
      window.alert('Please fill in all required fields: Spare, Asset Code, and Location');
      return;
    }

    setSaving(true);
    try {
      await onSave(formData);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="modal fade"
      id="spareSiteMapModal"
      tabIndex={-1}
      aria-labelledby="spareSiteMapModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="spareSiteMapModalLabel">{mapping ? 'Edit Mapping' : 'Add New Spare-Site-Location Mapping'}</h5>
            <button
              type="button"
              className="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
              onClick={onClose}
            />
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              {loading ? (
                <div className="p-3 text-center">Loading...</div>
              ) : (
                <>
                  <div className="mb-3">
                    <label className="form-label">
                      Spare <span className="text-danger">*</span>
                    </label>
                    <select
                      className="form-select"
                      value={formData.spare_id || ''}
                      onChange={(e) => setFormData({ ...formData, spare_id: parseInt(e.target.value) })}
                      required
                      disabled={!!mapping} // Cannot change spare in edit mode
                    >
                      <option value="">Select Spare</option>
                      {spares.map((spare) => (
                        <option key={spare.spare_id} value={spare.spare_id}>
                          {spare.spare_code} - {spare.spare_name}
                        </option>
                      ))}
                    </select>
                    {mapping && <small className="text-muted">Spare cannot be changed</small>}
                  </div>

                  <div className="mb-3">
                    <label className="form-label">
                      Asset Code (Site) <span className="text-danger">*</span>
                    </label>
                    <select
                      className="form-select"
                      value={formData.asset_code || ''}
                      onChange={(e) => setFormData({ ...formData, asset_code: e.target.value })}
                      required
                      disabled={!!mapping} // Cannot change asset in edit mode
                    >
                      <option value="">Select Asset</option>
                      {assets.map((asset) => (
                        <option key={asset.asset_code} value={asset.asset_code}>
                          {asset.asset_code} - {asset.asset_name}
                        </option>
                      ))}
                    </select>
                    {mapping && <small className="text-muted">Asset cannot be changed</small>}
                  </div>

                  <div className="mb-3">
                    <label className="form-label">
                      Location <span className="text-danger">*</span>
                    </label>
                    <select
                      className="form-select"
                      value={formData.location_id || ''}
                      onChange={(e) => setFormData({ ...formData, location_id: parseInt(e.target.value) })}
                      required
                      disabled={!!mapping} // Cannot change location in edit mode
                    >
                      <option value="">Select Location</option>
                      {locations.map((location) => (
                        <option key={location.location_id} value={location.location_id}>
                          {location.location_code} - {location.location_name}
                        </option>
                      ))}
                    </select>
                    {mapping && <small className="text-muted">Location cannot be changed</small>}
                  </div>

                  <div className="mb-3">
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        checked={formData.is_active || false}
                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                        id="isActive"
                      />
                      <label className="form-check-label" htmlFor="isActive">
                        Is Active
                      </label>
                    </div>
                  </div>
                </>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving || loading}>
                {saving ? 'Saving...' : mapping ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
