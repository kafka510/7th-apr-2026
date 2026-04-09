/**
 * Delete Data Modal Component
 */
 
import { useState } from 'react';
import { deleteData } from '../api';
import type { DataType } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface DeleteDataModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

export function DeleteDataModal({ onClose, onSuccess }: DeleteDataModalProps) {
  const { theme } = useTheme();
  const [dataType, setDataType] = useState<DataType | ''>('');
  const [deleteOption, setDeleteOption] = useState<'all' | 'date_range'>('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Theme-aware colors
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  const handleDelete = async () => {
    if (!dataType) {
      return;
    }

    if (deleteOption === 'date_range' && (!startDate || !endDate)) {
      return;
    }

    setShowConfirm(true);
  };

  const confirmDelete = async () => {
    if (!dataType) {
      return;
    }

    try {
      setLoading(true);
      const result = await deleteData({
        data_type: dataType as DataType,
        delete_option: deleteOption,
        start_date: deleteOption === 'date_range' ? startDate : undefined,
        end_date: deleteOption === 'date_range' ? endDate : undefined,
      });

      if (result.success) {
        if (onSuccess) {
          onSuccess();
        }
        onClose();
      } else {
        alert(`Error: ${result.error || 'Failed to delete data'}`);
      }
    } catch (error) {
      alert(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
      setShowConfirm(false);
    }
  };

  return (
    <>
      <div className="modal fade show" style={{ display: 'block' }} tabIndex={-1}>
        <div className="modal-dialog">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title font-bold" style={{ color: textPrimary }}>Delete Data</h5>
              <button type="button" className="btn-close" onClick={onClose}></button>
            </div>
            <div className="modal-body">
              <div className="alert alert-warning">
                <strong className="font-bold" style={{ color: textPrimary }}>⚠️ Warning:</strong>{' '}
                <span className="font-medium" style={{ color: textPrimary }}>This action cannot be undone!</span>
              </div>
              <div className="mb-3">
                <label htmlFor="deleteDataType" className="form-label font-semibold" style={{ color: textPrimary }}>
                  Data Type
                </label>
                <select
                  className="form-select"
                  id="deleteDataType"
                  value={dataType}
                  onChange={(e) => setDataType(e.target.value as DataType)}
                >
                  <option value="">Select Data Type</option>
                  <option value="yield">Yield Data</option>
                  <option value="bess">BESS Data</option>
                  <option value="bess_v1">BESS V1 Data</option>
                  <option value="aoc">AOC Data</option>
                  <option value="ice">ICE Data</option>
                  <option value="icvsexvscur">IC Budget vs Expected Data</option>
                  <option value="map">Map Data</option>
                  <option value="minamata">Minamata String Loss</option>
                  <option value="loss_calculation">Loss Calculation</option>
                  <option value="actual_generation_daily">Actual Generation Daily</option>
                  <option value="expected_budget_daily">Expected Budget Daily</option>
                  <option value="budget_gii_daily">Budget GII Daily</option>
                  <option value="actual_gii_daily">Actual GII Daily</option>
                  <option value="ic_approved_budget_daily">IC Approved Budget Daily</option>
                </select>
              </div>
              <div className="mb-3">
                <label className="form-label font-semibold" style={{ color: textPrimary }}>Delete Options</label>
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="radio"
                    name="deleteOption"
                    id="deleteAll"
                    value="all"
                    checked={deleteOption === 'all'}
                    onChange={(e) => setDeleteOption(e.target.value as 'all' | 'date_range')}
                  />
                  <label className="form-check-label font-medium" style={{ color: textPrimary }} htmlFor="deleteAll">
                    Delete all data
                  </label>
                </div>
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="radio"
                    name="deleteOption"
                    id="deleteDateRange"
                    value="date_range"
                    checked={deleteOption === 'date_range'}
                    onChange={(e) => setDeleteOption(e.target.value as 'all' | 'date_range')}
                  />
                  <label className="form-check-label font-medium" style={{ color: textPrimary }} htmlFor="deleteDateRange">
                    Delete by date range
                  </label>
                </div>
              </div>
              {deleteOption === 'date_range' && (
                <div className="mb-3">
                  <div className="row">
                    <div className="col-md-6">
                      <label htmlFor="deleteStartDate" className="form-label font-medium" style={{ color: textPrimary }}>
                        Start Date
                      </label>
                      <input
                        type="date"
                        className="form-control"
                        id="deleteStartDate"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                      />
                    </div>
                    <div className="col-md-6">
                      <label htmlFor="deleteEndDate" className="form-label font-medium" style={{ color: textPrimary }}>
                        End Date
                      </label>
                      <input
                        type="date"
                        className="form-control"
                        id="deleteEndDate"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleDelete}
                disabled={!dataType || (deleteOption === 'date_range' && (!startDate || !endDate))}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show" onClick={onClose}></div>

      {/* Confirmation Modal */}
      {showConfirm && (
        <>
          <div className="modal fade show" style={{ display: 'block', zIndex: 1055 }} tabIndex={-1}>
            <div className="modal-dialog">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title font-bold" style={{ color: textPrimary }}>Confirm Delete</h5>
                  <button type="button" className="btn-close" onClick={() => setShowConfirm(false)}></button>
                </div>
                <div className="modal-body">
                  <div className="alert alert-danger">
                    <strong className="font-bold" style={{ color: textPrimary }}>⚠️ Warning:</strong>
                    <br />
                    <span className="font-medium" style={{ color: textPrimary }}>
                      Are you sure you want to delete {dataType} data?
                      {deleteOption === 'date_range' && (
                        <>
                          <br />
                          <br />
                          Date Range: {startDate} to {endDate}
                        </>
                      )}
                      {deleteOption === 'all' && (
                        <>
                          <br />
                          <br />
                          This will delete ALL data of this type.
                        </>
                      )}
                      <br />
                      <br />
                      This action cannot be undone!
                    </span>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowConfirm(false)}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={confirmDelete}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                        Deleting...
                      </>
                    ) : (
                      'Confirm Delete'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div
            className="modal-backdrop fade show"
            style={{ zIndex: 1050 }}
            onClick={() => setShowConfirm(false)}
          ></div>
        </>
      )}
    </>
  );
}

