 
import { useEffect, useState } from 'react';
import type { DeviceMapping } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (mapping: Partial<DeviceMapping>) => Promise<void> | void;
  mapping: DeviceMapping | null;
}

const defaultMapping: Partial<DeviceMapping> = {
  asset_code: '',
  device_type: '',
  oem_tag: '',
  description: '',
  data_type: '',
  units: '',
  metric: '',
  fault_code: '',
  module_no: '',
  default_value: '',
};

export function DeviceMappingFormModal({ isOpen, onClose, onSave, mapping }: Props) {
  const [formData, setFormData] = useState<Partial<DeviceMapping>>(defaultMapping);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setFormData(mapping ? { ...defaultMapping, ...mapping } : defaultMapping);
      const modalEl = document.getElementById('deviceMappingModal');
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
  }, [isOpen, mapping, onClose]);

  const handleChange = (field: keyof DeviceMapping, value: string | number) => {
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
    <div className="modal fade" id="deviceMappingModal" tabIndex={-1} aria-hidden="true">
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900">
              {mapping ? 'Edit Device Mapping' : 'Add Device Mapping'}
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
                  <label className="form-label font-bold text-slate-900">
                    Device Type <span className="text-danger">*</span>
                  </label>
                  <input
                    className="form-control"
                    value={formData.device_type || ''}
                    onChange={(e) => handleChange('device_type', e.target.value)}
                    required
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    OEM Tag <span className="text-danger">*</span>
                  </label>
                  <input
                    className="form-control"
                    value={formData.oem_tag || ''}
                    onChange={(e) => handleChange('oem_tag', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    Metric <span className="text-danger">*</span>
                  </label>
                  <input
                    className="form-control"
                    value={formData.metric || ''}
                    onChange={(e) => handleChange('metric', e.target.value)}
                    required
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Units</label>
                  <input
                    className="form-control"
                    value={formData.units || ''}
                    onChange={(e) => handleChange('units', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Data Type</label>
                  <input
                    className="form-control"
                    value={formData.data_type || ''}
                    onChange={(e) => handleChange('data_type', e.target.value)}
                  />
                </div>

                <div className="col-12 mb-3">
                  <label className="form-label font-bold text-slate-900">Description</label>
                  <textarea
                    className="form-control"
                    rows={2}
                    value={formData.description || ''}
                    onChange={(e) => handleChange('description', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Fault Code</label>
                  <input
                    className="form-control"
                    value={formData.fault_code || ''}
                    onChange={(e) => handleChange('fault_code', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Module No</label>
                  <input
                    className="form-control"
                    value={formData.module_no || ''}
                    onChange={(e) => handleChange('module_no', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Default Value</label>
                  <input
                    className="form-control"
                    value={formData.default_value || ''}
                    onChange={(e) => handleChange('default_value', e.target.value)}
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


