/**
 * PV Module Import Modal Component
 * Modal for importing PV module datasheets from CSV
 */
import React, { useState, useRef } from 'react';
import type { ImportResult } from '../types/pvModules';

interface PVModuleImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (file: File, mode: 'create' | 'update' | 'both') => Promise<ImportResult | null>;
  onDownloadTemplate: () => Promise<void>;
  onAddManually?: () => void;
}

export const PVModuleImportModal: React.FC<PVModuleImportModalProps> = ({
  isOpen,
  onClose,
  onImport,
  onDownloadTemplate,
  onAddManually,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<'create' | 'update' | 'both'>('create');
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setImporting(true);
    try {
      const importResult = await onImport(file, mode);
      setResult(importResult);
      
      // Auto-close after 3 seconds if all successful
      if (importResult && importResult.failed === 0) {
        setTimeout(() => {
          handleClose();
        }, 3000);
      }
    } finally {
      setImporting(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose();
  };

  const handleDownloadTemplate = async () => {
    await onDownloadTemplate();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="modal-content w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <div className="modal-header mb-6 flex items-center justify-between">
          <h3 className="text-dark text-2xl font-bold">
            📥 Import PV Module Datasheets
          </h3>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600"
            type="button"
          >
            ✕
          </button>
        </div>

        {/* Instructions */}
        <div className="bg-light mb-6 rounded-lg border p-4">
          <h4 className="fw-semibold text-dark mb-2">📋 Import Instructions</h4>
          <ol className="text-dark list-inside list-decimal space-y-1 text-sm">
            <li>Download the CSV template below</li>
            <li>Fill in your module datasheet information</li>
            <li>Upload the completed CSV file</li>
            <li>Select import mode (create new, update existing, or both)</li>
            <li>Click Import button to process</li>
          </ol>
        </div>
        
        {/* Manual Add Option */}
        {onAddManually && (
          <div className="border-info bg-light mb-6 rounded-lg border-2 border-dashed p-4 text-center">
            <p className="text-dark mb-3">Prefer to enter module details manually?</p>
            <button
              type="button"
              onClick={() => { handleClose(); onAddManually(); }}
              className="btn btn-outline-primary"
            >
              ➕ Add Module Manually
            </button>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className={`mb-6 rounded-lg p-4 ${result.failed === 0 ? 'bg-green-50' : 'bg-yellow-50'}`}>
            <div className={`mb-2 font-semibold ${result.failed === 0 ? 'text-green-800' : 'text-yellow-800'}`}>
              Import Complete
            </div>
            <div className={`space-y-1 text-sm ${result.failed === 0 ? 'text-green-700' : 'text-yellow-700'}`}>
              <div>✓ Successfully imported: {result.success}</div>
              {result.failed !== undefined && result.failed > 0 && <div>✗ Failed: {result.failed}</div>}
              {result.errors && result.errors.length > 0 && (
                <div className="mt-2">
                  <div className="font-medium">Errors:</div>
                  <ul className="ml-4 list-inside list-disc">
                    {result.errors.slice(0, 5).map((error, idx) => (
                      <li key={idx} className="text-xs">
                        {error.row ? `Row ${error.row}: ` : ''}{error.message}
                      </li>
                    ))}
                    {result.errors.length > 5 && (
                      <li className="text-xs">... and {result.errors.length - 5} more</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Template Download */}
          <div className="mb-6">
            <button
              type="button"
              onClick={handleDownloadTemplate}
              className="btn btn-success w-100 border-dashed"
            >
              📄 Download CSV Template
            </button>
          </div>

          {/* Import Mode */}
          <div className="mb-6">
            <label className="fw-medium text-dark mb-2 block text-sm">Import Mode</label>
            <div className="space-y-2">
              <label className="text-dark flex items-center">
                <input
                  type="radio"
                  name="mode"
                  value="create"
                  checked={mode === 'create'}
                  onChange={(e) => setMode(e.target.value as 'create')}
                  className="form-check-input me-2"
                />
                <span>
                  <strong>Create Only</strong> - Add new modules (skip duplicates)
                </span>
              </label>
              <label className="text-dark flex items-center">
                <input
                  type="radio"
                  name="mode"
                  value="update"
                  checked={mode === 'update'}
                  onChange={(e) => setMode(e.target.value as 'update')}
                  className="form-check-input me-2"
                />
                <span>
                  <strong>Update Only</strong> - Update existing modules (skip new)
                </span>
              </label>
              <label className="text-dark flex items-center">
                <input
                  type="radio"
                  name="mode"
                  value="both"
                  checked={mode === 'both'}
                  onChange={(e) => setMode(e.target.value as 'both')}
                  className="form-check-input me-2"
                />
                <span>
                  <strong>Create & Update</strong> - Create new and update existing
                </span>
              </label>
            </div>
          </div>

          {/* File Upload */}
          <div className="mb-6">
            <label className="fw-medium text-dark mb-2 block text-sm">Select CSV File</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="form-control"
              required
            />
            {file && (
              <div className="text-dark mt-2 text-sm">
                Selected: <span className="fw-medium">{file.name}</span> ({(file.size / 1024).toFixed(1)} KB)
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-secondary"
              disabled={importing}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={importing || !file}
            >
              {importing ? 'Importing...' : '📥 Import Modules'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

