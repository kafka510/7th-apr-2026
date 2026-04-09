import { useCallback, useEffect, useState } from 'react';
import type { AssetContract, PaginatedResponse } from '../types';
import {
  fetchAssetContracts,
  createAssetContract,
  updateAssetContract,
  deleteAssetContract,
  downloadData,
  downloadTemplate,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { useTheme } from '../../../contexts/ThemeContext';

type FormState = Partial<AssetContract>;
type FieldKind = 'text' | 'number' | 'date' | 'json' | 'checkbox';
type ContractField = { key: keyof AssetContract; label: string; kind: FieldKind };

const FORM_FIELDS: ContractField[] = [
  { key: 'asset_number', label: 'Asset Number *', kind: 'text' },
  { key: 'asset_code', label: 'Asset Code *', kind: 'text' },
  { key: 'asset_name', label: 'Asset Name', kind: 'text' },
  { key: 'customer_asset_name', label: 'Customer Asset Name', kind: 'text' },
  { key: 'customer_tax_number', label: 'Customer Tax Number', kind: 'text' },
  { key: 'asset_address', label: 'Asset Address', kind: 'text' },
  { key: 'asset_cod', label: 'Asset COD', kind: 'date' },
  { key: 'contractor_name', label: 'Contractor Name', kind: 'text' },
  { key: 'spv_name', label: 'SPV Name', kind: 'text' },
  { key: 'contract_start_date', label: 'Contract Start Date', kind: 'date' },
  { key: 'contract_end_date', label: 'Contract End Date', kind: 'date' },
  { key: 'contract_billing_cycle', label: 'Contract Billing Cycle', kind: 'text' },
  { key: 'contract_billing_cycle_start_day', label: 'Billing Cycle Start Day', kind: 'number' },
  { key: 'contract_billing_cycle_end_day', label: 'Billing Cycle End Day', kind: 'number' },
  { key: 'currency_code', label: 'Currency Code', kind: 'text' },
  { key: 'sp_account_no', label: 'SP Account No', kind: 'text' },
  { key: 'escalation_condition', label: 'Escalation Condition', kind: 'text' },
  { key: 'escalation_type', label: 'Escalation Type', kind: 'text' },
  { key: 'escalation_grace_years', label: 'Escalation Grace Years', kind: 'number' },
  { key: 'escalation_rate', label: 'Escalation Rate', kind: 'number' },
  { key: 'escalation_period', label: 'Escalation Period', kind: 'number' },
  { key: 'due_days', label: 'Payment Due Days', kind: 'number' },
  { key: 'gst_rate', label: 'GST Rate (decimal)', kind: 'number' },
  { key: 'spv_address', label: 'SPV Address', kind: 'text' },
  { key: 'spv_gst_number', label: 'SPV GST Number', kind: 'text' },
  { key: 'contractor_id', label: 'Contractor ID', kind: 'text' },
  { key: 'contract_type', label: 'Contract Type (ERH profile)', kind: 'text' },
  { key: 'requires_utility_invoice', label: 'Requires utility invoice', kind: 'checkbox' },
  { key: 'bank_name', label: 'Bank Name', kind: 'text' },
  { key: 'bank_account_no', label: 'Bank Account No', kind: 'text' },
  { key: 'bank_swift', label: 'Bank SWIFT', kind: 'text' },
  { key: 'bank_branch_code', label: 'Bank Branch Code', kind: 'text' },
  { key: 'contractor_address', label: 'Contractor Address', kind: 'text' },
  { key: 'contact_person_1', label: 'Contact Person 1', kind: 'text' },
  { key: 'contact_person_2', label: 'Contact Person 2', kind: 'text' },
  { key: 'contact_person_3', label: 'Contact Person 3', kind: 'text' },
  { key: 'contact_person_4', label: 'Contact Person 4', kind: 'text' },
  { key: 'contact_person_5', label: 'Contact Person 5', kind: 'text' },
  { key: 'contact_person_6', label: 'Contact Person 6', kind: 'text' },
  { key: 'contact_email_id_1', label: 'Contact Email 1', kind: 'text' },
  { key: 'contact_email_id_2', label: 'Contact Email 2', kind: 'text' },
  { key: 'contact_email_id_3', label: 'Contact Email 3', kind: 'text' },
  { key: 'contact_email_id_4', label: 'Contact Email 4', kind: 'text' },
  { key: 'contact_email_id_5', label: 'Contact Email 5', kind: 'text' },
  { key: 'contact_email_id_6', label: 'Contact Email 6', kind: 'text' },
  { key: 'contact_email_id_7', label: 'Contact Email 7', kind: 'text' },
  { key: 'contact_number_1', label: 'Contact Number 1', kind: 'text' },
  { key: 'contact_number_2', label: 'Contact Number 2', kind: 'text' },
  { key: 'contact_number_3', label: 'Contact Number 3', kind: 'text' },
  { key: 'grid_export_rate', label: 'Grid Export Rate', kind: 'number' },
  { key: 'grid_export_tax', label: 'Grid Export Tax', kind: 'number' },
  { key: 'grid_excess_export', label: 'Grid Excess Export', kind: 'number' },
  { key: 'grid_excess_export_tax', label: 'Grid Excess Export Tax', kind: 'number' },
  { key: 'rooftop_self_consumption_rate', label: 'Rooftop Self Consumption Rate', kind: 'number' },
  { key: 'rooftop_self_consumption_tax', label: 'Rooftop Self Consumption Tax', kind: 'number' },
  { key: 'solar_lease_rate', label: 'Solar Lease Rate', kind: 'number' },
  { key: 'solar_lease_rate_tax', label: 'Solar Lease Rate Tax', kind: 'number' },
  { key: 'bess_dispatch_rate', label: 'BESS Dispatch Rate', kind: 'number' },
  { key: 'bess_dispatch_tax', label: 'BESS Dispatch Tax', kind: 'number' },
  { key: 'hybrid_solar_bess_rate', label: 'Hybrid Solar BESS Rate', kind: 'number' },
  { key: 'hybrid_solar_bess_tax', label: 'Hybrid Solar BESS Tax', kind: 'number' },
  { key: 'generation_based_ppa_rate', label: 'Generation Based PPA Rate', kind: 'number' },
  { key: 'generation_based_ppa_tax', label: 'Generation Based PPA Tax', kind: 'number' },
  { key: 'capacity_payment_rate', label: 'Capacity Payment Rate', kind: 'number' },
  { key: 'capacity_payment_tax', label: 'Capacity Payment Tax', kind: 'number' },
  { key: 'curtailment_compensation', label: 'Curtailment Compensation', kind: 'number' },
  { key: 'peak_tariff_rate', label: 'Peak Tariff Rate', kind: 'number' },
  { key: 'off_peak_rate', label: 'Off Peak Rate', kind: 'number' },
  { key: 'shoulder_tariff', label: 'Shoulder Tariff', kind: 'text' },
  { key: 'shoulder_rate', label: 'Shoulder Rate', kind: 'number' },
  { key: 'super_off_break_tariff', label: 'Super Off Break Tariff', kind: 'text' },
  { key: 'super_off_break_rate', label: 'Super Off Break Rate', kind: 'number' },
  { key: 'seasonal_tou_tariff', label: 'Seasonal TOU Tariff', kind: 'text' },
  { key: 'seasonal_tou_rate', label: 'Seasonal TOU Rate', kind: 'number' },
  { key: 'real_time_tou_tariff', label: 'Real Time TOU Tariff', kind: 'text' },
  { key: 'real_time_tou_rate', label: 'Real Time TOU Rate', kind: 'number' },
  { key: 'critical_peak_tariff', label: 'Critical Peak Tariff', kind: 'text' },
  { key: 'critical_peak_rate', label: 'Critical Peak Rate', kind: 'number' },
  { key: 'merchant_market_rate', label: 'Merchant Market Rate', kind: 'number' },
  { key: 'ancillary_services_charges', label: 'Ancillary Services Charges', kind: 'number' },
  { key: 'ancillary_services_tax', label: 'Ancillary Services Tax', kind: 'number' },
  { key: 'virtual_ppa_rate', label: 'Virtual PPA Rate', kind: 'number' },
  { key: 'virtual_ppa_tax', label: 'Virtual PPA Tax', kind: 'number' },
  { key: 'green_tariff_rate', label: 'Green Tariff Rate', kind: 'number' },
  { key: 'green_tariff_tax', label: 'Green Tariff Tax', kind: 'number' },
  { key: 'tariff_matrix_json', label: 'Tariff Matrix JSON', kind: 'json' },
];

const TABLE_COLUMNS: Array<keyof AssetContract> = FORM_FIELDS.map((f) => f.key);

export function AssetContractsTab() {
  const { theme } = useTheme();
  const [rows, setRows] = useState<AssetContract[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [canDelete, setCanDelete] = useState(false);
  const [toDelete, setToDelete] = useState<AssetContract | null>(null);
  const [editing, setEditing] = useState<AssetContract | null>(null);
  const [form, setForm] = useState<FormState>({});

  const showAlert = (message: string, type: 'success' | 'danger' | 'warning' | 'info') => {
    window.alert(`[${type.toUpperCase()}] ${message}`);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchAssetContracts(currentPage, pageSize, search);
      setRows((response as PaginatedResponse<AssetContract>).data || []);
      setTotalPages(response.total_pages || 0);
      setCanDelete(Boolean(response.can_delete));
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to load asset contracts', 'danger');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openNew = () => {
    setEditing(null);
    setForm({
      contract_billing_cycle: 'monthly',
      currency_code: 'SGD',
      requires_utility_invoice: false,
      due_days: 0,
    });
    setFormOpen(true);
  };

  const openEdit = (row: AssetContract) => {
    setEditing(row);
    setForm({ ...row });
    setFormOpen(true);
  };

  const onSave = async () => {
    try {
      if (!form.asset_number || !form.asset_code) {
        showAlert('Asset Number and Asset Code are required', 'warning');
        return;
      }
      if (editing?.id) {
        await updateAssetContract({ ...(form as AssetContract), id: editing.id });
        showAlert('Asset contract updated successfully', 'success');
      } else {
        await createAssetContract(form);
        showAlert('Asset contract created successfully', 'success');
      }
      setFormOpen(false);
      setEditing(null);
      await loadData();
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to save asset contract', 'danger');
    }
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    try {
      await deleteAssetContract(toDelete.id);
      showAlert('Asset contract deleted successfully', 'success');
      setDeleteModalOpen(false);
      setToDelete(null);
      await loadData();
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to delete asset contract', 'danger');
    }
  };

  const updateCheckbox = (key: keyof AssetContract, checked: boolean) => {
    setForm((p) => ({ ...p, [key]: checked as never }));
  };

  const updateField = (key: keyof AssetContract, kind: FieldKind, raw: string) => {
    if (kind === 'checkbox') {
      return;
    }
    if (kind === 'number') {
      setForm((p) => ({ ...p, [key]: raw === '' ? null : Number(raw) }));
      return;
    }
    if (kind === 'json') {
      try {
        const parsed = raw.trim() === '' ? null : JSON.parse(raw);
        setForm((p) => ({ ...p, [key]: parsed }));
      } catch {
        setForm((p) => ({ ...p, [key]: raw as never }));
      }
      return;
    }
    setForm((p) => ({ ...p, [key]: raw as never }));
  };

  return (
    <div className="card mt-3" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff' }}>
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0 font-bold">📄 Asset Contracts</h5>
        <div>
          <button className="btn btn-outline-info btn-sm" onClick={() => downloadTemplate('assets_contracts')}>
            📋 Download Template
          </button>
          <button className="btn btn-success btn-sm ms-2" onClick={() => downloadData('assets_contracts')}>
            📥 Download CSV
          </button>
          <button className="btn btn-primary btn-sm ms-2" onClick={() => setUploadModalOpen(true)}>
            📤 Upload CSV
          </button>
        </div>
      </div>
      <div className="card-body">
        <div className="row mb-3">
          <div className="col-md-6">
            <input className="form-control" placeholder="Search contracts..." value={search} onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }} />
          </div>
          <div className="col-md-6 text-end">
            <button className="btn btn-success btn-sm me-2" onClick={openNew}>➕ Add Contract</button>
            <select className="form-select" style={{ width: 'auto', display: 'inline-block' }} value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
        </div>

        {loading ? <div className="text-center"><div className="spinner-border" /></div> : (
          <div style={{ overflow: 'auto', maxHeight: 600 }}>
            <style>{`
              #asset-contracts-table th.sticky-actions-header {
                position: sticky !important;
                right: 0 !important;
                z-index: 102 !important;
                background: ${theme === 'dark' ? 'rgba(30, 41, 59, 0.95)' : '#212529'} !important;
                min-width: 140px !important;
                width: 140px !important;
                box-shadow: -3px 0 6px rgba(0,0,0,0.2) !important;
                border-left: 2px solid ${theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : '#495057'} !important;
                color: ${theme === 'dark' ? '#f1f5f9' : '#ffffff'} !important;
              }
              #asset-contracts-table td.sticky-actions-cell {
                position: sticky !important;
                right: 0 !important;
                z-index: 101 !important;
                background: ${theme === 'dark' ? 'rgba(15, 23, 42, 0.9)' : '#ffffff'} !important;
                min-width: 140px !important;
                width: 140px !important;
                white-space: nowrap !important;
                box-shadow: -3px 0 6px rgba(0,0,0,0.2) !important;
                text-align: center !important;
                border-left: 2px solid ${theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'} !important;
              }
            `}</style>
            <table className="table table-striped table-hover" id="asset-contracts-table">
              <thead>
                <tr>
                  {TABLE_COLUMNS.map((col) => (
                    <th key={String(col)}>{String(col)}</th>
                  ))}
                  <th className="sticky-actions-header">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? <tr><td colSpan={TABLE_COLUMNS.length + 1} className="text-center">No contracts found</td></tr> : rows.map((row) => (
                  <tr key={row.id}>
                    {TABLE_COLUMNS.map((col) => (
                      <td key={`${row.id}-${String(col)}`}>
                        {typeof row[col] === 'object' && row[col] !== null ? JSON.stringify(row[col]) : String(row[col] ?? '')}
                      </td>
                    ))}
                    <td className="sticky-actions-cell">
                      <button className="btn btn-outline-primary btn-sm me-2" onClick={() => openEdit(row)}>✏️</button>
                      {canDelete && (
                        <button className="btn btn-outline-danger btn-sm" onClick={() => { setToDelete(row); setDeleteModalOpen(true); }}>🗑️</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
      </div>

      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName="assets_contracts"
        onUploadSuccess={() => { showAlert('CSV uploaded successfully', 'success'); loadData(); }}
        onError={(msg) => showAlert(msg, 'danger')}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => { setDeleteModalOpen(false); setToDelete(null); }}
        onConfirm={confirmDelete}
        title="Confirm Delete"
        message={`Delete contract "${toDelete?.asset_number || ''}"?`}
        itemName={toDelete?.asset_number}
      />

      {formOpen && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">{editing ? 'Edit Contract' : 'Add Contract'}</h5>
                <button type="button" className="btn-close" onClick={() => setFormOpen(false)} />
              </div>
              <div className="modal-body">
                <div className="row g-2">
                  {FORM_FIELDS.map((f) => {
                    const value = form[f.key];
                    return (
                      <div className="col-md-4" key={String(f.key)}>
                        <label className="form-label">{f.label}</label>
                        {f.kind === 'checkbox' ? (
                          <div className="form-check">
                            <input
                              type="checkbox"
                              className="form-check-input"
                              checked={Boolean(value)}
                              onChange={(e) => updateCheckbox(f.key, e.target.checked)}
                            />
                          </div>
                        ) : (
                          <input
                            type={f.kind === 'date' ? 'date' : f.kind === 'number' ? 'number' : 'text'}
                            className="form-control"
                            value={f.kind === 'json' ? (typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? '')) : String(value ?? '')}
                            onChange={(e) => updateField(f.key, f.kind, e.target.value)}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setFormOpen(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={onSave}>Save</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

