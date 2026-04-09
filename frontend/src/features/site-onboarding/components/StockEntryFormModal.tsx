import { useState, useEffect } from 'react';
import type { StockEntry, SpareMaster, LocationMaster } from '../types';
import { fetchSpareMaster, fetchLocationMaster } from '../api';

interface StockEntryFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<StockEntry>) => void;
}

export function StockEntryFormModal({ isOpen, onClose, onSave }: StockEntryFormModalProps) {
  const [formData, setFormData] = useState<Partial<StockEntry>>({
    spare_id: undefined,
    location_id: undefined,
    quantity: 0,
    entry_type: 'Purchase',
    reference_number: '',
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
        entry_type: 'Purchase',
        reference_number: '',
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
      const modalElement = document.getElementById('stockEntryModal');
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
    if (!formData.spare_id || !formData.location_id || !formData.quantity || !formData.entry_type) {
      window.alert('Please fill in all required fields: Spare, Location, Quantity, and Entry Type');
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
      id="stockEntryModal"
      tabIndex={-1}
      aria-labelledby="stockEntryModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="stockEntryModalLabel">Stock Entry (IN)</h5>
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
                        Entry Type <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.entry_type || ''}
                        onChange={(e) => setFormData({ ...formData, entry_type: e.target.value })}
                        required
                      >
                        <option value="Purchase">Purchase</option>
                        <option value="Repair Return">Repair Return</option>
                        <option value="Initial Stock">Initial Stock</option>
                        <option value="Transfer In">Transfer In</option>
                        <option value="Adjustment">Adjustment</option>
                      </select>
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Reference Number</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.reference_number || ''}
                      onChange={(e) => setFormData({ ...formData, reference_number: e.target.value })}
                      placeholder="e.g., PO-001, Invoice-123"
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
                {saving ? 'Saving...' : 'Create Entry'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
