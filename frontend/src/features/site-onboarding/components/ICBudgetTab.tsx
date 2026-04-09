 
import { useCallback, useEffect, useState } from 'react';
import type { ICBudget } from '../types';
import {
  fetchICBudget,
  createICBudget,
  updateICBudget,
  deleteICBudget,
  downloadData,
  downloadTemplate,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { ICBudgetFormModal } from './ICBudgetFormModal';
import { useTheme } from '../../../contexts/ThemeContext';

export function ICBudgetTab() {
  const { theme } = useTheme();
  const [icBudgets, setIcBudgets] = useState<ICBudget[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [assetFilter, setAssetFilter] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [budgetToDelete, setBudgetToDelete] = useState<number | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<ICBudget | null>(null);

  const loadBudgets = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchICBudget(currentPage, pageSize, search, assetFilter);
      setIcBudgets(response.ic_budgets);
      setTotalPages(response.pagination.total_pages);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to load IC budgets');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search, assetFilter]);

  useEffect(() => {
    loadBudgets();
  }, [loadBudgets]);

  const handleSave = async (data: Partial<ICBudget>) => {
    try {
      if (editingBudget) {
        await updateICBudget({ ...data, id: editingBudget.id });
        window.alert('IC budget updated successfully');
      } else {
        await createICBudget(data);
        window.alert('IC budget created successfully');
      }
      setFormModalOpen(false);
      setEditingBudget(null);
      loadBudgets();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to save IC budget');
    }
  };

  const confirmDelete = async () => {
    if (budgetToDelete == null) return;
    try {
      await deleteICBudget(budgetToDelete);
      window.alert('IC budget deleted successfully');
      loadBudgets();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to delete IC budget');
    } finally {
      setDeleteModalOpen(false);
      setBudgetToDelete(null);
    }
  };

  // Theme-aware colors
  const tableBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#212529';
  const tableHeaderText = theme === 'dark' ? '#f1f5f9' : '#ffffff';
  const tableRowBg = theme === 'dark' ? 'transparent' : 'transparent';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowTextSecondary = theme === 'dark' ? '#cbd5e0' : '#4a5568';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';
  const tableStripeBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.1)' : 'rgba(0, 0, 0, 0.05)';

  return (
    <div className="card mt-3" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
      <div className="card-header d-flex justify-content-between align-items-center" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
        <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>📊 IC Budget</h5>
        <div>
          <button
            className="btn btn-outline-info btn-sm"
            onClick={() => downloadTemplate('ic_budget')}
            title="Download CSV template"
          >
            📋 Download Template
          </button>
          <button className="btn btn-success btn-sm ms-2" onClick={() => downloadData('ic_budget')}>
            📥 Download CSV
          </button>
          <button className="btn btn-primary btn-sm ms-2" onClick={() => setUploadModalOpen(true)}>
            📤 Upload CSV
          </button>
        </div>
      </div>
      <div className="card-body" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#ffffff' }}>
        <div className="row mb-3">
          <div className="col-md-5">
            <input
              type="text"
              className="form-control"
              placeholder="Search IC budgets..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            />
          </div>
          <div className="col-md-3">
            <input
              type="text"
              className="form-control"
              placeholder="Filter by asset code"
              value={assetFilter}
              onChange={(e) => {
                setAssetFilter(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            />
          </div>
          <div className="col-md-2">
            <select
              className="form-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            >
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
          <div className="col-md-2 text-end">
            <button className="btn btn-success btn-sm" onClick={() => setFormModalOpen(true)}>
              ➕ Add IC Budget
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-5 text-center">
            <div className="spinner-border" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : (
          <>
            <style>{`
              #ic-budget-table-container {
                position: relative;
                overflow-x: scroll;
                overflow-y: auto;
                max-height: 600px;
                width: 100%;
                border: 1px solid ${tableBorder};
                border-radius: 0.375rem;
                -webkit-overflow-scrolling: touch;
                background: ${tableBg};
              }
              #ic-budget-table {
                width: max-content;
                min-width: 100%;
                margin-bottom: 0;
                border-collapse: separate;
                border-spacing: 0;
                background: ${tableBg};
              }
              #ic-budget-table thead th {
                background: ${tableHeaderBg} !important;
                color: ${tableHeaderText} !important;
                border-color: ${tableBorder} !important;
              }
              #ic-budget-table tbody td {
                background: ${tableRowBg} !important;
                color: ${tableRowText} !important;
                border-color: ${tableBorder} !important;
              }
              #ic-budget-table tbody tr:hover td {
                background: ${tableRowHoverBg} !important;
              }
              #ic-budget-table.table-striped tbody tr:nth-of-type(odd) td {
                background: ${tableRowBg} !important;
              }
              #ic-budget-table.table-striped tbody tr:nth-of-type(even) td {
                background: ${tableStripeBg} !important;
              }
              #ic-budget-table.table-striped tbody tr:nth-of-type(even):hover td {
                background: ${tableRowHoverBg} !important;
              }
            `}</style>
            <div id="ic-budget-table-container">
              <table className="table-striped table-hover table" id="ic-budget-table">
                <thead>
                  <tr>
                    <th>Asset Code</th>
                    <th>Asset Number</th>
                    <th>Month</th>
                    <th>Month Date</th>
                    <th>IC BD Production</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {icBudgets.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center font-medium" style={{ color: tableRowTextSecondary }}>
                        No IC budget records found
                      </td>
                    </tr>
                  ) : (
                    icBudgets.map((budget) => (
                      <tr key={budget.id}>
                        <td className="font-medium" style={{ color: tableRowText }}>{budget.asset_code}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{budget.asset_number || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{budget.month_str}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{budget.month_date || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{budget.ic_bd_production ?? '-'}</td>
                        <td>
                        <button
                          className="btn btn-outline-primary btn-sm me-2"
                          onClick={() => {
                            setEditingBudget(budget);
                            setFormModalOpen(true);
                          }}
                        >
                          ✏️
                        </button>
                        <button
                          className="btn btn-outline-danger btn-sm"
                          onClick={() => {
                            setBudgetToDelete(budget.id);
                            setDeleteModalOpen(true);
                          }}
                        >
                          🗑️
                        </button>
                      </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {!loading && totalPages > 1 && (
          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />
        )}
      </div>

      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName="ic_budget"
        onUploadSuccess={() => {
          setUploadModalOpen(false);
          loadBudgets();
        }}
        onError={(msg) => window.alert(msg)}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setBudgetToDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete IC Budget"
        message="Are you sure you want to delete this record?"
      />

      <ICBudgetFormModal
        isOpen={formModalOpen}
        onClose={() => {
          setFormModalOpen(false);
          setEditingBudget(null);
        }}
        onSave={handleSave}
        budget={editingBudget}
      />
    </div>
  );
}
