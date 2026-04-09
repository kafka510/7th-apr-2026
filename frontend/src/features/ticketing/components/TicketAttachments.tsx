import { useRef, useState, useCallback, useEffect } from 'react';

import { uploadTicketAttachment, uploadPastedImage } from '../api';
import type { TicketAttachment } from '../types';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

type TicketAttachmentsProps = {
  ticketId: string;
  attachments: TicketAttachment[];
  loading?: boolean;
  onUpdate?: () => void;
};

export const TicketAttachments = ({ ticketId, attachments, loading = false, onUpdate }: TicketAttachmentsProps) => {
  const [expanded, setExpanded] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const handleFileSelect = useCallback((file: File) => {
    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      setError(`File size exceeds maximum allowed size of 10MB`);
      return;
    }
    setSelectedFile(file);
    setError(null);
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      return;
    }

    setUploading(true);
    setError(null);

    try {
      await uploadTicketAttachment(ticketId, selectedFile);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (onUpdate) {
        onUpdate();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const handlePaste = useCallback(async (e: ClipboardEvent) => {
    // Only handle paste when the component is expanded and focused
    if (!expanded || document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
      return;
    }

    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault();
        const blob = item.getAsFile();
        if (blob) {
          // Convert blob to base64
          const reader = new FileReader();
          reader.onloadend = async () => {
            const base64data = reader.result as string;
            setUploading(true);
            setError(null);
            try {
              await uploadPastedImage(ticketId, base64data);
              if (onUpdate) {
                onUpdate();
              }
            } catch (err) {
              setError(err instanceof Error ? err.message : 'Failed to upload pasted image');
            } finally {
              setUploading(false);
            }
          };
          reader.readAsDataURL(blob);
        }
        break;
      }
    }
  }, [ticketId, expanded, onUpdate]);

  useEffect(() => {
    if (expanded) {
      document.addEventListener('paste', handlePaste);
      return () => {
        document.removeEventListener('paste', handlePaste);
      };
    }
  }, [expanded, handlePaste]);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Attachments</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="p-4">
          {loading ? (
            <p className="text-sm text-slate-500">Loading attachments…</p>
          ) : (
            <>
              {/* Upload Section */}
              <div
                ref={dropZoneRef}
                onDragEnter={handleDragEnter}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`mb-4 rounded-lg border-2 border-dashed p-4 transition-colors ${
                  isDragging
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-slate-300 bg-slate-50'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      Choose File
                    </label>
                    <input
                      id="file-upload"
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      onChange={handleFileInputChange}
                      disabled={uploading}
                    />
                    {selectedFile ? (
                      <span className="text-xs text-slate-700">{selectedFile.name}</span>
                    ) : (
                      <span className="text-xs text-slate-500">No file chosen</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500">
                    <p>Max: 10MB</p>
                    <p>Drag and drop files here, or paste images (Ctrl+V)</p>
                  </div>
                  {error && (
                    <div className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-xs text-rose-700">
                      {error}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={handleUpload}
                    disabled={!selectedFile || uploading}
                    className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {uploading ? 'Uploading...' : '↑ Upload File'}
                  </button>
                </div>
              </div>

              {/* Attachments List */}
              {attachments.length === 0 ? (
                <p className="text-sm text-slate-500">No attachments</p>
              ) : (
                <ul className="space-y-3 text-sm text-slate-700">
                  {attachments.map((attachment) => (
                    <li
                      key={attachment.id}
                      className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
                    >
                      <div>
                        <p className="font-semibold text-slate-900">{attachment.file_name}</p>
                        <p className="text-xs text-slate-500">
                          Uploaded by {attachment.uploaded_by?.name ?? 'Unknown'} ·{' '}
                          {new Date(attachment.created_at).toLocaleString()}
                        </p>
                      </div>
                      <a
                        href={attachment.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600 transition hover:border-sky-300 hover:text-sky-600"
                      >
                        Download
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
