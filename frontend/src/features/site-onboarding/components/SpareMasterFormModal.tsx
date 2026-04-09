import { useState, useEffect } from 'react';
import type { SpareMaster } from '../types';

interface SpareMasterFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<SpareMaster>) => void;
  spare: SpareMaster | null;
}

export function SpareMasterFormModal({ isOpen, onClose, onSave, spare }: SpareMasterFormModalProps) {
  const [formData, setFormData] = useState<Partial<SpareMaster>>({
    spare_code: '',
    spare_name: '',
    description: '',
    category: '',
    unit: '',
    min_stock: null,
    max_stock: null,
    is_critical: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (spare) {
        // Edit mode
        setFormData({
          spare_code: spare.spare_code,
          spare_name: spare.spare_name,
          description: spare.description || '',
          category: spare.category || '',
          unit: spare.unit,
          min_stock: spare.min_stock,
          max_stock: spare.max_stock,
          is_critical: spare.is_critical,
        });
      } else {
        // Add mode
        setFormData({
          spare_code: '',
          spare_name: '',
          description: '',
          category: '',
          unit: '',
          min_stock: null,
          max_stock: null,
          is_critical: false,
        });
      }
    }
  }, [isOpen, spare]);

  useEffect(() => {
    if (isOpen) {
      const modalElement = document.getElementById('spareMasterModal');
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
    if (!formData.spare_code || !formData.spare_name || !formData.unit) {
      window.alert('Please fill in all required fields: Spare Code, Spare Name, and Unit');
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
      id="spareMasterModal"
      tabIndex={-1}
      aria-labelledby="spareMasterModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="spareMasterModalLabel">{spare ? 'Edit Spare' : 'Add New Spare'}</h5>
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
              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label">
                    Spare Code <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.spare_code || ''}
                    onChange={(e) => setFormData({ ...formData, spare_code: e.target.value })}
                    required
                    disabled={!!spare} // Cannot edit spare_code
                  />
                  {spare && <small className="text-muted">Spare code cannot be changed</small>}
                </div>
                <div className="col-md-6">
                  <label className="form-label">
                    Spare Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.spare_name || ''}
                    onChange={(e) => setFormData({ ...formData, spare_name: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label">Category</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.category || ''}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    placeholder="e.g., Electrical, Mechanical"
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">
                    Unit <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.unit || ''}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    placeholder="e.g., Pcs, Kg, Liters"
                    required
                  />
                </div>
              </div>

              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label">Min Stock</label>
                  <input
                    type="number"
                    className="form-control"
                    value={formData.min_stock ?? ''}
                    onChange={(e) => setFormData({ ...formData, min_stock: e.target.value ? parseInt(e.target.value) : null })}
                    min="0"
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Max Stock</label>
                  <input
                    type="number"
                    className="form-control"
                    value={formData.max_stock ?? ''}
                    onChange={(e) => setFormData({ ...formData, max_stock: e.target.value ? parseInt(e.target.value) : null })}
                    min="0"
                  />
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">Description</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description of the spare part"
                />
              </div>

              <div className="mb-3">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    checked={formData.is_critical || false}
                    onChange={(e) => setFormData({ ...formData, is_critical: e.target.checked })}
                    id="isCritical"
                  />
                  <label className="form-check-label" htmlFor="isCritical">
                    Is Critical Spare
                  </label>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : spare ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
