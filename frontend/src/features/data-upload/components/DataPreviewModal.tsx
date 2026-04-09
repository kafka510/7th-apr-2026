/**
 * Data Preview Modal Component
 */
 
import { useState, useEffect, useRef } from 'react';
import { fetchDataPreview } from '../api';
import type { DataType } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface DataPreviewModalProps {
  onClose: () => void;
}

export function DataPreviewModal({ onClose }: DataPreviewModalProps) {
  const { theme } = useTheme();
  const [dataType, setDataType] = useState<DataType>('yield');
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const modalContentRef = useRef<HTMLDivElement>(null);

  // Theme-aware colors
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textTertiary = theme === 'dark' ? '#64748b' : '#94a3b8';

  const loadPreview = async () => {
    try {
      setLoading(true);
      setError(null);
      setMessage(null);
      const result = await fetchDataPreview(dataType);
      
      // Handle different response shapes
      let previewData: Record<string, unknown>[] = [];
      if (Array.isArray(result)) {
        previewData = result;
      } else if (result && Array.isArray(result.preview)) {
        // API v2 format: { preview: [], status: "success", total_records: 0 }
        previewData = result.preview;
        if (result.total_records !== undefined) {
          setMessage(result.total_records === 0 ? `No records found (total: ${result.total_records})` : null);
        }
      } else if (result && Array.isArray(result.data)) {
        // Standard format: { data: [] }
        previewData = result.data;
        if ('message' in result && result.message) {
          setMessage(result.message);
        }
      } else if (result && 'results' in result && Array.isArray((result as any).results)) {
        previewData = (result as any).results;
      } else if (result && result.data) {
        previewData = Array.isArray(result.data) ? result.data : [];
        if ('message' in result && result.message) {
          setMessage(result.message);
        }
      }
      
      setData(previewData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataType]);

  const headers = data.length > 0 ? Object.keys(data[0]) : [];

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
        <div className="modal-dialog modal-xl">
          <div className="modal-content" ref={modalContentRef}>
            <div className="modal-header">
            <h5 className="modal-title font-bold" style={{ color: textPrimary }}>Data Preview</h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="previewDataType" className="form-label font-semibold" style={{ color: textPrimary }}>
                Data Type
              </label>
              <select
                className="form-select"
                id="previewDataType"
                value={dataType}
                onChange={(e) => setDataType(e.target.value as DataType)}
              >
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
            <div className="table-responsive" style={{ maxHeight: '500px', overflowY: 'auto' }}>
              <table className="table-striped table-bordered table" style={{ width: '100%' }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: theme === 'dark' ? '#1e293b' : '#ffffff', zIndex: 10 }}>
                  <tr>
                    {loading ? (
                      <th className="font-bold" style={{ color: textPrimary }}>Loading...</th>
                    ) : headers.length > 0 ? (
                      headers.map((header) => (
                        <th key={header} className="font-bold" style={{ color: textPrimary, padding: '8px', border: `1px solid ${theme === 'dark' ? '#475569' : '#cbd5e1'}` }}>
                          {header}
                        </th>
                      ))
                    ) : (
                      <th className="font-bold" style={{ color: textPrimary }}>No data</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={headers.length || 1} className="text-center font-medium" style={{ color: textTertiary, padding: '20px' }}>
                        <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                        Loading data...
                      </td>
                    </tr>
                  ) : error ? (
                    <tr>
                      <td colSpan={headers.length || 1} className="text-center font-medium" style={{ color: '#dc2626', padding: '20px' }}>
                        Error: {error}
                      </td>
                    </tr>
                  ) : data.length === 0 ? (
                    <tr>
                      <td colSpan={headers.length || 1} className="text-center font-medium" style={{ color: textTertiary, padding: '20px' }}>
                        {message || 'No data available'}
                      </td>
                    </tr>
                  ) : (
                    data.map((row, index) => (
                      <tr key={index}>
                        {headers.map((header) => (
                          <td key={header} className="font-medium" style={{ color: textPrimary, padding: '8px', border: `1px solid ${theme === 'dark' ? '#475569' : '#cbd5e1'}` }}>
                            {String(row[header] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
          </div>
        </div>
      </div>
    </>
  );
}

