import { useState, useEffect } from 'react';
import type { LocationMaster } from '../types';

interface LocationMasterFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<LocationMaster>) => void;
  location: LocationMaster | null;
}

export function LocationMasterFormModal({ isOpen, onClose, onSave, location }: LocationMasterFormModalProps) {
  const [formData, setFormData] = useState<Partial<LocationMaster>>({
    location_code: '',
    location_name: '',
    location_type: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (location) {
        // Edit mode
        setFormData({
          location_code: location.location_code,
          location_name: location.location_name,
          location_type: location.location_type || '',
        });
      } else {
        // Add mode
        setFormData({
          location_code: '',
          location_name: '',
          location_type: '',
        });
      }
    }
  }, [isOpen, location]);

  useEffect(() => {
    if (isOpen) {
      const modalElement = document.getElementById('locationMasterModal');
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
    if (!formData.location_code || !formData.location_name) {
      window.alert('Please fill in all required fields: Location Code and Location Name');
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
      id="locationMasterModal"
      tabIndex={-1}
      aria-labelledby="locationMasterModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="locationMasterModalLabel">{location ? 'Edit Location' : 'Add New Location'}</h5>
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
              <div className="mb-3">
                <label className="form-label">
                  Location Code <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.location_code || ''}
                  onChange={(e) => setFormData({ ...formData, location_code: e.target.value })}
                  required
                  disabled={!!location} // Cannot edit location_code
                  placeholder="e.g., WH-001"
                />
                {location && <small className="text-muted">Location code cannot be changed</small>}
              </div>

              <div className="mb-3">
                <label className="form-label">
                  Location Name <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.location_name || ''}
                  onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                  required
                  placeholder="e.g., Main Warehouse"
                />
              </div>

              <div className="mb-3">
                <label className="form-label">Location Type</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.location_type || ''}
                  onChange={(e) => setFormData({ ...formData, location_type: e.target.value })}
                  placeholder="e.g., Warehouse, Site Store, Van"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : location ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
