 
import { useState } from 'react';

interface MarkAttendedModalProps {
  onClose: () => void;
  onConfirm: (adminResponse: string) => void;
}

export function MarkAttendedModal({ onClose, onConfirm }: MarkAttendedModalProps) {
  const [adminResponse, setAdminResponse] = useState('');

  const handleSubmit = () => {
    onConfirm(adminResponse.trim());
  };

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative mx-4 w-full max-w-2xl rounded-xl border border-slate-800/80 bg-gradient-to-br from-slate-900/95 to-slate-800/95 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-gradient-to-r from-green-600/10 to-sky-600/10 p-4">
          <h5 className="flex items-center gap-2 text-lg font-bold text-green-400">
            ✓ Mark Feedback as Attended
          </h5>
          <button
            type="button"
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 p-4">
          <div>
            <label htmlFor="adminResponseText" className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-slate-300">
              💭 Additional Message (Optional)
            </label>
            <textarea
              id="adminResponseText"
              rows={4}
              value={adminResponse}
              onChange={(e) => setAdminResponse(e.target.value)}
              placeholder="Enter any additional message or response to include in the thank you email..."
              className="w-full rounded-lg border border-slate-700/70 bg-slate-900/80 px-3 py-2 text-sm text-slate-200 shadow-inner transition-all duration-200 placeholder:text-slate-500 hover:border-sky-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/30"
            />
            <div className="mt-1.5 text-xs text-slate-400">
              ℹ️ This message will be included in the thank you email sent to the user. Leave blank for a standard response.
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-xl border border-blue-600/50 bg-blue-600/10 p-3">
            <span className="text-lg">📧</span>
            <div className="text-sm text-blue-200">
              <span className="font-semibold">Note:</span> A thank you email will be sent to the user once you confirm this action.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-slate-800 bg-slate-900/50 p-4">
          <button
            type="button"
            className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-sm font-semibold text-slate-300 transition-colors hover:border-slate-600 hover:bg-slate-800 hover:text-slate-200"
            onClick={onClose}
          >
            ✕ Cancel
          </button>
          <button
            type="button"
            className="rounded-lg border border-green-600/50 bg-green-600/20 px-4 py-2 text-sm font-semibold text-green-300 transition-colors hover:border-green-500 hover:bg-green-600/30"
            onClick={handleSubmit}
          >
            ✓ Mark as Attended & Send Email
          </button>
        </div>
      </div>
    </div>
  );
}

