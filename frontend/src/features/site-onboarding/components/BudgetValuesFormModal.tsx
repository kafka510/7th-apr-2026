 
import { useEffect, useState } from 'react';
import type { BudgetValues } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (budget: Partial<BudgetValues>) => Promise<void> | void;
  budget: BudgetValues | null;
}

const defaultBudget: Partial<BudgetValues> = {
  asset_number: '',
  asset_code: '',
  month_str: '',
  month_date: '',
  bd_production: 0,
  bd_ghi: 0,
  bd_gti: 0,
};

export function BudgetValuesFormModal({ isOpen, onClose, onSave, budget }: Props) {
  const [formData, setFormData] = useState<Partial<BudgetValues>>(defaultBudget);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setFormData(budget ? { ...defaultBudget, ...budget } : defaultBudget);
      const modalEl = document.getElementById('budgetValuesModal');
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

  const handleChange = (field: keyof BudgetValues, value: string | number) => {
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
    <div className="modal fade" id="budgetValuesModal" tabIndex={-1} aria-hidden="true">
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900">
              {budget ? 'Edit Budget Value' : 'Add Budget Value'}
            </h5>
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

                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">BD Production</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.bd_production ?? ''}
                    onChange={(e) => handleChange('bd_production', e.target.value ? parseFloat(e.target.value) : 0)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">BD GHI</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.bd_ghi ?? ''}
                    onChange={(e) => handleChange('bd_ghi', e.target.value ? parseFloat(e.target.value) : 0)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">BD GTI</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.bd_gti ?? ''}
                    onChange={(e) => handleChange('bd_gti', e.target.value ? parseFloat(e.target.value) : 0)}
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


