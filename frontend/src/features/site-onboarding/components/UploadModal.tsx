 
import { useState, useEffect, type ChangeEvent, type FormEvent } from 'react';
import type { TableName, UploadResponse } from '../types';
import { uploadCSVFile } from '../api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  tableName: TableName;
  onUploadSuccess: () => void;
  onError: (message: string) => void;
}

export function UploadModal({
  isOpen,
  onClose,
  tableName,
  onUploadSuccess,
  onError,
}: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);

  useEffect(() => {
    if (isOpen) {
      const modalElement = document.getElementById('uploadModal');
      if (modalElement) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const modal = new (window as any).bootstrap.Modal(modalElement);
        modal.show();

        const handleHidden = () => {
          setFile(null);
          setUploadResult(null);
          onClose();
        };
        modalElement.addEventListener('hidden.bs.modal', handleHidden);

        return () => {
          modalElement.removeEventListener('hidden.bs.modal', handleHidden);
          modal.dispose();
        };
      }
    }
  }, [isOpen, onClose]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUploadResult(null);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      onError('Please select a file');
      return;
    }

    setUploading(true);
    setUploadResult(null);

    try {
      const result = await uploadCSVFile(tableName, file);
      setUploadResult(result);
      if (result.success) {
        setTimeout(() => {
          onUploadSuccess();
          const modalElement = document.getElementById('uploadModal');
          if (modalElement) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const modal = (window as any).bootstrap.Modal.getInstance(modalElement);
            modal?.hide();
          }
        }, 2000);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="modal fade"
      id="uploadModal"
      tabIndex={-1}
      aria-labelledby="uploadModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900" id="uploadModalLabel">
              Upload CSV - {tableName.replace('_', ' ').toUpperCase()}
            </h5>
            <button
              type="button"
              className="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
              onClick={onClose}
            />
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor="csvFile" className="form-label font-bold text-slate-900">
                  Select CSV File
                </label>
                <input
                  type="file"
                  className="form-control"
                  id="csvFile"
                  accept=".csv"
                  onChange={handleFileChange}
                  required
                  disabled={uploading}
                />
              </div>

              {uploadResult && (
                <div className={`alert alert-${uploadResult.success ? 'success' : 'danger'}`}>
                  <div className="font-medium text-slate-900">
                    {uploadResult.message || uploadResult.error || 'Upload completed'}
                  </div>
                  {uploadResult.error && !uploadResult.success && (
                    <div className="mt-2">
                      <div className="mb-2 font-bold text-slate-900">Detailed Error:</div>
                      <div className="mb-2 font-medium text-slate-700">{uploadResult.error}</div>
                      {uploadResult.error_examples && uploadResult.error_examples.length > 0 && (
                        <div className="mt-2">
                          <strong className="font-bold text-slate-900">Example Errors:</strong>
                          <ul className="mt-1 font-medium text-slate-700">
                            {uploadResult.error_examples.map((example, idx) => (
                              <li key={idx} style={{ fontSize: '0.9em' }}>{example}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {uploadResult.help_text && (
                        <div className="bg-light mt-2 rounded p-2">
                          <strong className="font-bold text-slate-900">Help:</strong>
                          <pre className="mb-0 mt-1 font-medium text-slate-700" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85em' }}>
                            {uploadResult.help_text}
                          </pre>
                        </div>
                      )}
                      {uploadResult.validation_errors && uploadResult.validation_errors.length > 0 && (
                        <div className="mt-2">
                          <strong className="font-bold text-slate-900">
                            Validation Errors (showing first {uploadResult.validation_errors.length} of {uploadResult.total_errors || 'many'}):
                          </strong>
                          <div className="mt-1" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                            {uploadResult.validation_errors.map((err, idx) => (
                              <div key={idx} className="mb-1 font-medium text-slate-700" style={{ fontSize: '0.85em', padding: '4px', borderLeft: '3px solid #dc3545' }}>
                                {err.message || JSON.stringify(err)}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  {uploadResult.statistics && (
                    <div className="mt-2 font-medium text-slate-700">
                      <small>
                        Imported: {uploadResult.statistics.records_imported} | Skipped:{' '}
                        {uploadResult.statistics.records_skipped}
                      </small>
                    </div>
                  )}
                  {uploadResult.errors && uploadResult.errors.length > 0 && (
                    <div className="mt-2">
                      <strong className="font-bold text-slate-900">Errors:</strong>
                      <ul className="font-medium text-slate-700">
                        {uploadResult.errors.slice(0, 5).map((error, idx) => (
                          <li key={idx}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                data-bs-dismiss="modal"
                onClick={onClose}
                disabled={uploading}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={uploading || !file}>
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

