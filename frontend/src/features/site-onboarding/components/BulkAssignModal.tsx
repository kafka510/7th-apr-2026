/**
 * Bulk Assign Modal Component
 * Modal for bulk assigning PV module configuration to multiple devices
 */
import React, { useState, useEffect } from 'react';
import { usePVModules } from '../hooks/usePVModules';
import type { BulkAssignConfig } from '../types/pvModules';

interface BulkAssignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAssign: (config: Partial<BulkAssignConfig>) => Promise<{ success: number; failed: number } | null>;
  selectedDeviceIds: string[];
}

export const BulkAssignModal: React.FC<BulkAssignModalProps> = ({
  isOpen,
  onClose,
  onAssign,
  selectedDeviceIds,
}) => {
  const { modules } = usePVModules();
  const [formData, setFormData] = useState<Partial<BulkAssignConfig>>({});
  const [assigning, setAssigning] = useState(false);
  const [result, setResult] = useState<{ success: number; failed: number } | null>(null);

  useEffect(() => {
    if (isOpen) {
      // Reset form when modal opens
      setFormData({});
      setResult(null);
    }
  }, [isOpen]);

  const handleChange = (field: keyof BulkAssignConfig, value: BulkAssignConfig[keyof BulkAssignConfig]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Auto-calculate string rated power when module and count are selected
    if (field === 'module_datasheet_id' || field === 'modules_in_series') {
      const moduleId = field === 'module_datasheet_id' ? value : formData.module_datasheet_id;
      const moduleCount = field === 'modules_in_series' ? value : formData.modules_in_series;
      
      if (moduleId && moduleCount) {
        const moduleIdNum = typeof moduleId === 'string' ? parseInt(moduleId, 10) : Number(moduleId);
        const moduleCountNum = typeof moduleCount === 'string' ? parseInt(moduleCount, 10) : Number(moduleCount);
        const selectedModule = modules.find(m => m.id === moduleIdNum);
        if (selectedModule) {
          setFormData(prev => ({
            ...prev,
            string_rated_power: selectedModule.pmax_stc * moduleCountNum,
          }));
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAssigning(true);
    
    try {
      const assignResult = await onAssign(formData);
      setResult(assignResult);
      
      // Auto-close after 2 seconds if all successful
      if (assignResult && assignResult.failed === 0) {
        setTimeout(() => {
          onClose();
        }, 2000);
      }
    } finally {
      setAssigning(false);
    }
  };

  if (!isOpen) return null;

  const selectedModule = formData.module_datasheet_id
    ? modules.find((m) => m.id === (typeof formData.module_datasheet_id === 'string' ? parseInt(formData.module_datasheet_id, 10) : Number(formData.module_datasheet_id)))
    : null;

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="modal-content max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
        <div className="modal-header mb-6 flex items-center justify-between">
          <h3 className="fw-bold text-dark text-2xl">
            {selectedDeviceIds.length === 1 ? '⚙️ Configure Device' : '🔧 Bulk Assign Configuration'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            type="button"
          >
            ✕
          </button>
        </div>

        {/* Selected Devices Info */}
        <div className="mb-6 rounded-lg bg-blue-50 p-4">
          <div className="font-semibold text-blue-800">
            Selected Devices: {selectedDeviceIds.length}
          </div>
          <div className="text-sm text-blue-600">
            Configuration will be applied to all selected string devices
          </div>
        </div>

        {/* Result Display */}
        {result && (
          <div className={`mb-6 rounded-lg p-4 ${result.failed === 0 ? 'bg-green-50' : 'bg-yellow-50'}`}>
            <div className={`font-semibold ${result.failed === 0 ? 'text-green-800' : 'text-yellow-800'}`}>
              ✓ Assignment Complete
            </div>
            <div className={`text-sm ${result.failed === 0 ? 'text-green-600' : 'text-yellow-600'}`}>
              Successfully assigned: {result.success} devices
              {result.failed > 0 && ` | Failed: ${result.failed} devices`}
            </div>
          </div>
        )}

          <form onSubmit={handleSubmit}>
            {/* Device Info */}
            <div className="bg-light mb-4 rounded-lg border p-3">
              <p className="text-dark mb-0">
                <strong>Configuring {selectedDeviceIds.length} device{selectedDeviceIds.length > 1 ? 's' : ''}:</strong>
                {selectedDeviceIds.length === 1 && (
                  <span className="badge bg-primary ms-2">{selectedDeviceIds[0]}</span>
                )}
                {selectedDeviceIds.length > 1 && (
                  <span className="text-muted ms-2">{selectedDeviceIds.join(', ')}</span>
                )}
              </p>
            </div>
            
            {/* Module Selection */}
            <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Module Configuration</h4>
            
            <div className="mb-4">
              <label className="fw-medium text-dark mb-1 block text-sm">
                Select PV Module Type
              </label>
              <select
                className="form-control"
                value={formData.module_datasheet_id || ''}
                onChange={(e) => handleChange('module_datasheet_id', e.target.value)}
              >
                <option value="">-- Select Module --</option>
                {modules.map((module) => (
                  <option key={module.id} value={module.id}>
                    {module.manufacturer} - {module.module_model} ({module.pmax_stc}Wp)
                  </option>
                ))}
              </select>
            </div>

            {selectedModule && (
              <div className="bg-light text-dark mb-4 rounded border p-3 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div><span className="fw-bold">Power:</span> {selectedModule.pmax_stc} Wp</div>
                  <div><span className="fw-bold">Efficiency:</span> {selectedModule.module_efficiency_stc}%</div>
                  <div><span className="fw-bold">Voc:</span> {selectedModule.voc_stc} V</div>
                  <div><span className="fw-bold">Isc:</span> {selectedModule.isc_stc} A</div>
                  <div><span className="fw-bold">Technology:</span> {selectedModule.technology}</div>
                  <div><span className="fw-bold">Cells:</span> {selectedModule.cells_per_module}</div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Modules in Series
                </label>
                <input
                  type="number"
                  className="form-control"
                  value={formData.modules_in_series || ''}
                  onChange={(e) => handleChange('modules_in_series', parseInt(e.target.value))}
                  placeholder="e.g., 24"
                  min="1"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  String Rated Power (W)
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control bg-light"
                  value={formData.string_rated_power || ''}
                  onChange={(e) => handleChange('string_rated_power', parseFloat(e.target.value))}
                  placeholder="Auto-calculated"
                  readOnly
                />
                <span className="text-dark text-xs">Calculated from module × count</span>
              </div>
            </div>
          </div>

          {/* Installation Details */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Installation Details</h4>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Tilt Angle (°)
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.tilt_angle || ''}
                  onChange={(e) => handleChange('tilt_angle', parseFloat(e.target.value))}
                  placeholder="e.g., 25"
                  min="0"
                  max="90"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Azimuth Angle (°)
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.azimuth_angle || ''}
                  onChange={(e) => handleChange('azimuth_angle', parseFloat(e.target.value))}
                  placeholder="e.g., 180 (South)"
                  min="0"
                  max="360"
                />
                <span className="text-dark text-xs">0°=North, 90°=East, 180°=South, 270°=West</span>
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Tracking Type
                </label>
                <select
                  className="form-control"
                  value={formData.tracking_type || ''}
                  onChange={(e) => handleChange('tracking_type', e.target.value)}
                >
                  <option value="">-- Select --</option>
                  <option value="fixed">Fixed</option>
                  <option value="single_axis">Single Axis</option>
                  <option value="dual_axis">Dual Axis</option>
                </select>
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Installation Date
                </label>
                <input
                  type="date"
                  className="form-control"
                  value={formData.installation_date || ''}
                  onChange={(e) => handleChange('installation_date', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Loss Factors */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Loss Factors (%)</h4>
            
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Soiling Loss
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.soiling_loss || ''}
                  onChange={(e) => handleChange('soiling_loss', parseFloat(e.target.value))}
                  placeholder="e.g., 2"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Shading Loss
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.shading_loss || ''}
                  onChange={(e) => handleChange('shading_loss', parseFloat(e.target.value))}
                  placeholder="e.g., 1"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Mismatch Loss
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.mismatch_loss || ''}
                  onChange={(e) => handleChange('mismatch_loss', parseFloat(e.target.value))}
                  placeholder="e.g., 1"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Wiring Loss
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.wiring_loss || ''}
                  onChange={(e) => handleChange('wiring_loss', parseFloat(e.target.value))}
                  placeholder="e.g., 1.5"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Availability Loss
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.availability_loss || ''}
                  onChange={(e) => handleChange('availability_loss', parseFloat(e.target.value))}
                  placeholder="e.g., 0.5"
                  min="0"
                  max="100"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
              disabled={assigning}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:bg-gray-400"
              disabled={assigning || !formData.module_datasheet_id}
            >
              {assigning ? 'Assigning...' : `Assign to ${selectedDeviceIds.length} Devices`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

