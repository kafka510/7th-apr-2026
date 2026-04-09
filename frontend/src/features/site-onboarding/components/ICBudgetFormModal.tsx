 
import { useEffect, useState } from 'react';
import type { ICBudget } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (budget: Partial<ICBudget>) => Promise<void> | void;
  budget: ICBudget | null;
}

const defaultBudget: Partial<ICBudget> = {
  asset_code: '',
  asset_number: '',
  month_str: '',
  month_date: '',
  ic_bd_production: 0,
};

export function ICBudgetFormModal({ isOpen, onClose, onSave, budget }: Props) {
  const [formData, setFormData] = useState<Partial<ICBudget>>(defaultBudget);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setFormData(budget ? { ...defaultBudget, ...budget } : defaultBudget);
      const modalEl = document.getElementById('icBudgetModal');
      if (modalEl) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const modal = new (window as any).bootstrap.Modal(modalEl);
        modal.show();
        const handleHidden = () => onClose();
        modalEl.addEventListener('hidden.bs.modal', handleHidden);
        return () => {
          modalEl.removeEventListener('hidden.bs.modal', handleHidden);
          modal.dispose();
        };
      }
    }
    return undefined;
  }, [isOpen, budget, onClose]);

  const handleChange = (field: keyof ICBudget, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(formData);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal fade" id="icBudgetModal" tabIndex={-1} aria-hidden="true">
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900">{budget ? 'Edit IC Budget' : 'Add IC Budget'}</h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close" />
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    Asset Code <span className="text-danger">*</span>
                  </label>
                  <input
                    className="form-control"
                    value={formData.asset_code || ''}
                    onChange={(e) => handleChange('asset_code', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Asset Number</label>
                  <input
                    className="form-control"
                    value={formData.asset_number || ''}
                    onChange={(e) => handleChange('asset_number', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    Month (e.g., JAN) <span className="text-danger">*</span>
                  </label>
                  <input
                    className="form-control"
                    value={formData.month_str || ''}
                    onChange={(e) => handleChange('month_str', e.target.value.toUpperCase())}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Month Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={formData.month_date ? formData.month_date.slice(0, 10) : ''}
                    onChange={(e) => handleChange('month_date', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">IC BD Production</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.ic_bd_production ?? ''}
                    onChange={(e) =>
                      handleChange('ic_bd_production', e.target.value ? parseFloat(e.target.value) : 0)
                    }
                  />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}


