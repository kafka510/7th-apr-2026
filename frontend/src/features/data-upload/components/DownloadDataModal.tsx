/**
 * Download Data Modal Component
 */

import { useState, useRef } from 'react';
import { downloadData } from '../api';
import type { DataType } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface DownloadDataModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

export function DownloadDataModal({ onClose, onSuccess }: DownloadDataModalProps) {
  const { theme } = useTheme();
  const [dataType, setDataType] = useState<DataType | ''>('');
  const [format, setFormat] = useState<'csv' | 'excel'>('csv');
  const [loading, setLoading] = useState(false);
  const modalContentRef = useRef<HTMLDivElement>(null);

  // Theme-aware colors
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  const handleDownload = async () => {
    if (!dataType) {
      alert('Please select a data type');
      return;
    }

    try {
      setLoading(true);
      await downloadData(dataType as DataType, format);
      
      if (onSuccess) {
        onSuccess();
      }
      onClose();
    } catch (error) {
      alert(`Error: ${error instanceof Error ? error.message : 'Failed to download data'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          zIndex: 9998,
        }}
        onClick={onClose}
      />
      {/* Modal */}
      <div
        className="modal fade show"
        style={{
          display: 'block',
          position: 'fixed',
          inset: 0,
          zIndex: 9999,
          pointerEvents: 'auto',
        }}
        tabIndex={-1}
      >
        <div className="modal-dialog">
          <div className="modal-content" ref={modalContentRef}>
            <div className="modal-header">
            <h5 className="modal-title font-bold" style={{ color: textPrimary }}>Download Data</h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="downloadDataType" className="form-label font-semibold" style={{ color: textPrimary }}>
                Data Type
              </label>
              <select
                className="form-select"
                id="downloadDataType"
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
              <label className="form-label font-semibold" style={{ color: textPrimary }}>File Format</label>
              <div className="form-check">
                <input
                  className="form-check-input"
                  type="radio"
                  name="downloadFormat"
                  id="formatCsv"
                  value="csv"
                  checked={format === 'csv'}
                  onChange={(e) => setFormat(e.target.value as 'csv' | 'excel')}
                />
                <label className="form-check-label font-medium" style={{ color: textPrimary }} htmlFor="formatCsv">
                  CSV (.csv)
                </label>
              </div>
              <div className="form-check">
                <input
                  className="form-check-input"
                  type="radio"
                  name="downloadFormat"
                  id="formatExcel"
                  value="excel"
                  checked={format === 'excel'}
                  onChange={(e) => setFormat(e.target.value as 'csv' | 'excel')}
                />
                <label className="form-check-label font-medium" style={{ color: textPrimary }} htmlFor="formatExcel">
                  Excel (.xlsx)
                </label>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleDownload}
              disabled={!dataType || loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                  Downloading...
                </>
              ) : (
                'Download'
              )}
            </button>
          </div>
          </div>
        </div>
      </div>
    </>
  );
}
