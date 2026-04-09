/**
 * Delete Confirmation Modal Component
 * Generic modal for confirming delete operations
 */
import React, { useState } from 'react';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (force: boolean) => Promise<boolean>;
  title: string;
  message: string;
  itemName: string;
  showForceOption?: boolean;
  warningMessage?: string;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  itemName,
  showForceOption = false,
  warningMessage,
}) => {
  const [deleting, setDeleting] = useState(false);
  const [force, setForce] = useState(false);

  const handleConfirm = async () => {
    setDeleting(true);
    try {
      const success = await onConfirm(force);
      if (success) {
        onClose();
      }
    } finally {
      setDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="modal-content w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="modal-header mb-4 flex items-center justify-between">
          <h3 className="text-xl font-bold text-red-600">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            type="button"
            disabled={deleting}
          >
            ✕
          </button>
        </div>

        <div className="mb-6">
          <p className="mb-4 text-gray-700">{message}</p>
          
          <div className="rounded bg-gray-100 p-3">
            <div className="text-sm text-gray-600">Item to delete:</div>
            <div className="text-dark font-semibold">{itemName}</div>
          </div>

          {warningMessage && (
            <div className="mt-4 rounded bg-yellow-50 p-3 text-sm text-yellow-800">
              ⚠️ {warningMessage}
            </div>
          )}

          {showForceOption && (
            <div className="mt-4">
              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={(e) => setForce(e.target.checked)}
                  className="mr-2 mt-1"
                />
                <span className="text-sm text-gray-700">
                  <strong>Force delete</strong> even if associated with devices
                  <div className="text-xs text-gray-500">
                    (This will clear module assignments from devices)
                  </div>
                </span>
              </label>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded border border-gray-300 bg-white px-6 py-2 text-gray-700 hover:bg-gray-50"
            disabled={deleting}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="rounded bg-red-600 px-6 py-2 text-white hover:bg-red-700 disabled:bg-gray-400"
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
};


