/**
 * PV Module Modal Component
 * Modal for creating or editing PV module datasheets
 */
import React, { useState, useEffect } from 'react';
import type { PVModuleDatasheet, ModuleTechnology } from '../types/pvModules';

interface PVModuleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (moduleData: Partial<PVModuleDatasheet>) => Promise<boolean>;
  editModule?: PVModuleDatasheet | null;
  mode: 'create' | 'edit';
}

export const PVModuleModal: React.FC<PVModuleModalProps> = ({
  isOpen,
  onClose,
  onSave,
  editModule,
  mode,
}) => {
  const [formData, setFormData] = useState<Partial<PVModuleDatasheet>>({
    technology: 'mono_perc',
    noct: 45.0,
    temp_coeff_type_voc: 'absolute',
    temp_coeff_type_isc: 'percentage',
  });
  const [saving, setSaving] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (editModule && mode === 'edit') {
        // Debug: Log the editModule data
        console.log('🔍 Edit Module Data:', editModule);
        
        // Simply copy all fields from editModule
        // Keep numeric values as numbers for HTML5 validation
        setFormData({ ...editModule });
        
        // Initialize raw numeric values for temperature coefficients
        const rawValues: Record<string, string> = {};
        if (editModule.temp_coeff_pmax !== null && editModule.temp_coeff_pmax !== undefined) {
          rawValues.temp_coeff_pmax = String(editModule.temp_coeff_pmax);
        }
        if (editModule.temp_coeff_voc !== null && editModule.temp_coeff_voc !== undefined) {
          rawValues.temp_coeff_voc = String(editModule.temp_coeff_voc);
        }
        if (editModule.temp_coeff_isc !== null && editModule.temp_coeff_isc !== undefined) {
          rawValues.temp_coeff_isc = String(editModule.temp_coeff_isc);
        }
        setRawNumericValues(rawValues);
        
        // Debug: Log formData after setting
        console.log('📝 Form Data Set:', { ...editModule });
        
        // Show advanced section if any advanced fields have values
        const hasAdvancedData = editModule.noct || editModule.low_irr_200 || editModule.low_irr_400 || 
                                editModule.low_irr_600 || editModule.low_irr_800 || editModule.warranty_year_1;
        setShowAdvanced(!!hasAdvancedData);
      } else if (mode === 'create') {
        console.log('➕ Create mode - resetting form');
        // Reset form for create mode
        setFormData({
          technology: 'mono_perc',
          noct: 45.0,
          temp_coeff_type_voc: 'absolute',
          temp_coeff_type_isc: 'percentage',
        });
        setRawNumericValues({});
        setShowAdvanced(false);
      }
    }
  }, [isOpen, editModule, mode]);

  // Store raw string values for numeric inputs to handle negative and decimal values properly
  const [rawNumericValues, setRawNumericValues] = useState<Record<string, string>>({});

  const handleChange = (field: keyof PVModuleDatasheet, value: number | string | boolean | null) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setFormData(prev => ({ ...prev, [field]: value as any }));
    
    // Auto-calculate area if length and width are provided
    if (field === 'length' || field === 'width') {
      const length = field === 'length' ? value : formData.length;
      const width = field === 'width' ? value : formData.width;
      
      // Convert to numbers for calculation
      const lengthNum = typeof length === 'number' ? length : (typeof length === 'string' ? parseFloat(length) : null);
      const widthNum = typeof width === 'number' ? width : (typeof width === 'string' ? parseFloat(width) : null);
      
      if (lengthNum && widthNum && typeof lengthNum === 'number' && typeof widthNum === 'number' && !isNaN(lengthNum) && !isNaN(widthNum)) {
        setFormData(prev => ({ ...prev, area: (lengthNum * widthNum) / 1000000 }));
      }
    }
  };

  // Handle numeric input change with proper negative/decimal support
  const handleNumericChange = (
    field: keyof PVModuleDatasheet,
    value: string,
    allowNegative: boolean = true
  ) => {
    // Store raw value for display
    setRawNumericValues(prev => ({ ...prev, [field]: value }));
    
    // Allow empty string, negative sign, decimal point, and partial numbers
    if (value === '' || value === '-' || value === '.' || value === '-.') {
      setFormData(prev => ({ ...prev, [field]: null }));
      return;
    }
    
    // Parse the value
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      // Check if negative values are allowed
      if (!allowNegative && numValue < 0) {
        return; // Don't update if negative not allowed
      }
      setFormData(prev => ({ ...prev, [field]: numValue }));
    }
  };

  // Get display value for numeric field (use raw if available, otherwise formatted)
  const getNumericDisplayValue = (field: keyof PVModuleDatasheet): string => {
    if (rawNumericValues[field] !== undefined) {
      return rawNumericValues[field];
    }
    return formData[field] !== null && formData[field] !== undefined ? String(formData[field]) : '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      // Data is already in correct format (numbers), just submit
      const success = await onSave(formData);
      if (success) {
        onClose();
      }
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="modal-content max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
        <div className="modal-header mb-6 flex items-center justify-between">
          <h3 className="fw-bold text-dark text-2xl">
            {mode === 'create' ? '➕ Add PV Module Datasheet' : '✏️ Edit PV Module Datasheet'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            type="button"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Basic Information */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Basic Information</h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Manufacturer <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.manufacturer || ''}
                  onChange={(e) => handleChange('manufacturer', e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Module Model <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.module_model || ''}
                  onChange={(e) => handleChange('module_model', e.target.value)}
                  required
                  placeholder="e.g., TSM-DE09.08"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">Technology</label>
                <select
                  className="form-control"
                  value={formData.technology || 'mono_perc'}
                  onChange={(e) => handleChange('technology', e.target.value as ModuleTechnology)}
                >
                  <option value="mono_perc">Monocrystalline PERC</option>
                  <option value="mono_standard">Monocrystalline Standard</option>
                  <option value="poly">Polycrystalline</option>
                  <option value="thin_film">Thin Film</option>
                  <option value="bifacial">Bifacial</option>
                  <option value="heterojunction">Heterojunction (HJT)</option>
                  <option value="topcon">TOPCon</option>
                </select>
              </div>
            </div>
          </div>

          {/* Electrical Characteristics - STC */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Electrical Characteristics (STC)</h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Pmax (Wp) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  value={formData.pmax_stc ?? ''}
                  onChange={(e) => handleChange('pmax_stc', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Voc (V) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  value={formData.voc_stc ?? ''}
                  onChange={(e) => handleChange('voc_stc', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Isc (A) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  value={formData.isc_stc ?? ''}
                  onChange={(e) => handleChange('isc_stc', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Vmp (V) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  value={formData.vmp_stc ?? ''}
                  onChange={(e) => handleChange('vmp_stc', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Imp (A) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  value={formData.imp_stc ?? ''}
                  onChange={(e) => handleChange('imp_stc', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Efficiency (%) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  value={formData.module_efficiency_stc ?? ''}
                  onChange={(e) => handleChange('module_efficiency_stc', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                />
              </div>
            </div>
          </div>

          {/* Temperature Coefficients */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Temperature Coefficients</h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Pmax (%/°C) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  inputMode="decimal"
                  className="form-control"
                  value={getNumericDisplayValue('temp_coeff_pmax')}
                  onChange={(e) => {
                    const value = e.target.value;
                    // Allow digits, negative sign, decimal point
                    if (value === '' || /^-?\d*\.?\d*$/.test(value)) {
                      handleNumericChange('temp_coeff_pmax', value);
                    }
                  }}
                  onBlur={(e) => {
                    // Validate on blur - ensure it's a valid number
                    const value = e.target.value;
                    if (value && value !== '-' && value !== '.' && value !== '-.') {
                      const numValue = parseFloat(value);
                      if (!isNaN(numValue)) {
                        setFormData(prev => ({ ...prev, temp_coeff_pmax: numValue }));
                        setRawNumericValues(prev => ({ ...prev, temp_coeff_pmax: String(numValue) }));
                      }
                    }
                  }}
                  required
                  placeholder="-0.34"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Voc <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    inputMode="decimal"
                    className="form-control flex-1"
                    value={getNumericDisplayValue('temp_coeff_voc')}
                    onChange={(e) => {
                      const value = e.target.value;
                      // Allow digits, negative sign, decimal point
                      if (value === '' || /^-?\d*\.?\d*$/.test(value)) {
                        handleNumericChange('temp_coeff_voc', value);
                      }
                    }}
                    onBlur={(e) => {
                      // Validate on blur
                      const value = e.target.value;
                      if (value && value !== '-' && value !== '.' && value !== '-.') {
                        const numValue = parseFloat(value);
                        if (!isNaN(numValue)) {
                          setFormData(prev => ({ ...prev, temp_coeff_voc: numValue }));
                          setRawNumericValues(prev => ({ ...prev, temp_coeff_voc: String(numValue) }));
                        }
                      }
                    }}
                    required
                    placeholder="-0.26"
                  />
                  <select
                    className="form-select"
                    style={{ maxWidth: '120px' }}
                    value={formData.temp_coeff_type_voc || 'absolute'}
                    onChange={(e) => handleChange('temp_coeff_type_voc', e.target.value)}
                  >
                    <option value="absolute">V/°C</option>
                    <option value="percentage">%/°C</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Isc <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    inputMode="decimal"
                    className="form-control flex-1"
                    value={getNumericDisplayValue('temp_coeff_isc')}
                    onChange={(e) => {
                      const value = e.target.value;
                      // Allow digits, negative sign, decimal point
                      if (value === '' || /^-?\d*\.?\d*$/.test(value)) {
                        handleNumericChange('temp_coeff_isc', value);
                      }
                    }}
                    onBlur={(e) => {
                      // Validate on blur
                      const value = e.target.value;
                      if (value && value !== '-' && value !== '.' && value !== '-.') {
                        const numValue = parseFloat(value);
                        if (!isNaN(numValue)) {
                          setFormData(prev => ({ ...prev, temp_coeff_isc: numValue }));
                          setRawNumericValues(prev => ({ ...prev, temp_coeff_isc: String(numValue) }));
                        }
                      }
                    }}
                    required
                    placeholder="0.048"
                  />
                  <select
                    className="form-select"
                    style={{ maxWidth: '120px' }}
                    value={formData.temp_coeff_type_isc || 'percentage'}
                    onChange={(e) => handleChange('temp_coeff_type_isc', e.target.value)}
                  >
                    <option value="absolute">A/°C</option>
                    <option value="percentage">%/°C</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Physical Characteristics */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">Physical Characteristics</h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Cells per Module
                </label>
                <input
                  type="number"
                  className="form-control"
                  value={formData.cells_per_module || ''}
                  onChange={(e) => handleChange('cells_per_module', parseInt(e.target.value))}
                  placeholder="e.g., 144 (optional if not in datasheet)"
                />
                <small className="text-muted">Usually 60, 72, 120, 132, or 144 cells. Skip if not specified.</small>
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Length (mm) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.length ?? ''}
                  onChange={(e) => handleChange('length', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                  placeholder="2187"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Width (mm) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control"
                  value={formData.width ?? ''}
                  onChange={(e) => handleChange('width', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  required
                  placeholder="1102"
                />
              </div>
              <div>
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Area (m²)
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control bg-light"
                  value={formData.area ?? ''}
                  readOnly
                  placeholder="Auto-calculated from length × width"
                />
                <small className="text-muted">Automatically calculated when length and width are entered</small>
              </div>
            </div>
          </div>

          {/* Advanced Fields (Collapsible) */}
          <div className="mb-6">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-4 hover:bg-gray-100"
            >
              <span className="fw-semibold text-dark">
                {showAdvanced ? '▼' : '▶'} Advanced Fields (Optional)
              </span>
              <span className="text-secondary text-sm">
                Low irradiance, warranty, NOCT, etc.
              </span>
            </button>

            {showAdvanced && (
              <div className="mt-4 rounded-lg border border-gray-200 p-4">
                {/* NOCT */}
                <div className="mb-4">
                  <h5 className="mb-2 font-medium text-gray-700">NOCT (Nominal Operating Cell Temperature)</h5>
                  <p className="text-muted mb-3 text-sm">
                    Temperature reached by cells in open-rack mounting at 800 W/m², 20°C ambient, 1 m/s wind.
                    Typically 42-47°C. Check datasheet&apos;s &quot;Operating Characteristics&quot; or &quot;Thermal&quot; section.
                  </p>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">NOCT (°C)</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.noct ?? ''}
                        onChange={(e) => handleChange('noct', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="45.0 (optional, use 45 if not specified)"
                      />
                    </div>
                  </div>
                </div>

                {/* Low Irradiance Performance */}
                <div className="mb-4">
                  <h5 className="mb-2 font-medium text-gray-700">Low Irradiance Performance (%)</h5>
                  <p className="text-muted mb-3 text-sm">
                    Module performance at different light levels compared to STC (1000 W/m²).
                    Optional - typically 96-99%. Found in &quot;Performance&quot; or &quot;Additional Data&quot; section of datasheet.
                  </p>
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">@ 200 W/m²</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.low_irr_200 ?? ''}
                        onChange={(e) => handleChange('low_irr_200', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="96"
                      />
                    </div>
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">@ 400 W/m²</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.low_irr_400 ?? ''}
                        onChange={(e) => handleChange('low_irr_400', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="98"
                      />
                    </div>
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">@ 600 W/m²</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.low_irr_600 ?? ''}
                        onChange={(e) => handleChange('low_irr_600', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="99"
                      />
                    </div>
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">@ 800 W/m²</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.low_irr_800 ?? ''}
                        onChange={(e) => handleChange('low_irr_800', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="99.5"
                      />
                    </div>
                  </div>
                </div>

                {/* Warranty Information */}
                <div>
                  <h5 className="mb-2 font-medium text-gray-700">Warranty Information</h5>
                  <p className="text-muted mb-3 text-sm">
                    Linear power warranty guarantees. Typical: 98% at Year 1, 84.8% at Year 25, 0.55%/year degradation.
                    Found in &quot;Product Warranty&quot; section. Optional if not specified.
                  </p>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">Year 1 Power (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.warranty_year_1 ?? ''}
                        onChange={(e) => handleChange('warranty_year_1', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="98"
                      />
                    </div>
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">Year 25 Power (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control"
                        value={formData.warranty_year_25 ?? ''}
                        onChange={(e) => handleChange('warranty_year_25', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="84.8"
                      />
                    </div>
                    <div>
                      <label className="fw-medium text-dark mb-1 block text-sm">Degradation (%/year)</label>
                      <input
                        type="number"
                        step="0.01"
                        className="form-control"
                        value={formData.linear_degradation_rate ?? ''}
                        onChange={(e) => handleChange('linear_degradation_rate', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                        placeholder="0.5"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-gray-300 bg-white px-6 py-2 text-gray-700 hover:bg-gray-50"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:bg-gray-400"
              disabled={saving}
            >
              {saving ? 'Saving...' : mode === 'create' ? 'Create Module' : 'Update Module'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};


