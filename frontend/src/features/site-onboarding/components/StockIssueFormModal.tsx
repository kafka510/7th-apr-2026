import { useState, useEffect } from 'react';
import type { StockIssue, SpareMaster, LocationMaster } from '../types';
import { fetchSpareMaster, fetchLocationMaster } from '../api';

interface StockIssueFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<StockIssue>) => void;
}

export function StockIssueFormModal({ isOpen, onClose, onSave }: StockIssueFormModalProps) {
  const [formData, setFormData] = useState<Partial<StockIssue>>({
    spare_id: undefined,
    location_id: undefined,
    quantity: 0,
    issue_type: 'Breakdown',
    ticket_id: '',
    issued_to: '',
    remarks: '',
  });
  const [saving, setSaving] = useState(false);
  const [spares, setSpares] = useState<SpareMaster[]>([]);
  const [locations, setLocations] = useState<LocationMaster[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Reset form
      setFormData({
        spare_id: undefined,
        location_id: undefined,
        quantity: 0,
        issue_type: 'Breakdown',
        ticket_id: '',
        issued_to: '',
        remarks: '',
      });

      // Load spares and locations
      setLoading(true);
      Promise.all([
        fetchSpareMaster(1, 1000, '').then(res => setSpares(res.data)),
        fetchLocationMaster(1, 1000, '').then(res => setLocations(res.data)),
      ]).finally(() => setLoading(false));
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      const modalElement = document.getElementById('stockIssueModal');
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
    if (!formData.spare_id || !formData.location_id || !formData.quantity || !formData.issue_type) {
      window.alert('Please fill in all required fields: Spare, Location, Quantity, and Issue Type');
      return;
    }

    if (formData.quantity <= 0) {
      window.alert('Quantity must be greater than 0');
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
      id="stockIssueModal"
      tabIndex={-1}
      aria-labelledby="stockIssueModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="stockIssueModalLabel">Stock Issue (OUT)</h5>
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
                  <div className="row mb-3">
                    <div className="col-md-6">
                      <label className="form-label">
                        Spare <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.spare_id || ''}
                        onChange={(e) => setFormData({ ...formData, spare_id: parseInt(e.target.value) })}
                        required
                      >
                        <option value="">Select Spare</option>
                        {spares.map((spare) => (
                          <option key={spare.spare_id} value={spare.spare_id}>
                            {spare.spare_code} - {spare.spare_name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">
                        Location <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.location_id || ''}
                        onChange={(e) => setFormData({ ...formData, location_id: parseInt(e.target.value) })}
                        required
                      >
                        <option value="">Select Location</option>
                        {locations.map((location) => (
                          <option key={location.location_id} value={location.location_id}>
                            {location.location_code} - {location.location_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="row mb-3">
                    <div className="col-md-6">
                      <label className="form-label">
                        Quantity <span className="text-danger">*</span>
                      </label>
                      <input
                        type="number"
                        className="form-control"
                        value={formData.quantity || ''}
                        onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })}
                        required
                        min="0.01"
                        step="0.01"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">
                        Issue Type <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.issue_type || ''}
                        onChange={(e) => setFormData({ ...formData, issue_type: e.target.value })}
                        required
                      >
                        <option value="Breakdown">Breakdown</option>
                        <option value="Preventive">Preventive</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Ticket ID (Optional)</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.ticket_id || ''}
                      onChange={(e) => setFormData({ ...formData, ticket_id: e.target.value })}
                      placeholder="UUID of linked ticket"
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Issued To</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.issued_to || ''}
                      onChange={(e) => setFormData({ ...formData, issued_to: e.target.value })}
                      placeholder="e.g., Site A Pump, Technician Name"
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Remarks</label>
                    <textarea
                      className="form-control"
                      rows={3}
                      value={formData.remarks || ''}
                      onChange={(e) => setFormData({ ...formData, remarks: e.target.value })}
                      placeholder="Additional notes"
                    />
                  </div>
                </>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving || loading}>
                {saving ? 'Saving...' : 'Create Issue'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
