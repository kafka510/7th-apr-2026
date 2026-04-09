 
import type { Feedback } from '../types';

interface MessageModalProps {
  feedback: Feedback;
  onClose: () => void;
  onViewImages?: () => void;
}

export function MessageModal({ feedback, onClose, onViewImages }: MessageModalProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const hasImages = feedback.images && feedback.images.length > 0;
  const imageCount = feedback.image_count || (feedback.images ? feedback.images.length : 0);

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
        <div className="flex items-center justify-between border-b border-slate-800 bg-gradient-to-r from-sky-600/10 to-purple-600/10 p-4">
          <h5 className="text-lg font-bold text-sky-400">
            💬 Feedback from {feedback.user.username}
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
        <div className="space-y-3 p-4">
          <div>
            <span className="text-sm font-semibold text-slate-400">Subject:</span>
            <div className="mt-1 text-base font-semibold text-slate-200">{feedback.subject}</div>
          </div>
          
          <div>
            <span className="text-sm font-semibold text-slate-400">From:</span>
            <div className="mt-1 text-sm text-slate-300">
              {feedback.user.username} ({feedback.user_email})
            </div>
          </div>
          
          <div>
            <span className="text-sm font-semibold text-slate-400">Date:</span>
            <div className="mt-1 text-sm text-slate-300">{formatDate(feedback.created_at)}</div>
          </div>
          
          <div>
            <span className="text-sm font-semibold text-slate-400">Message:</span>
            <div className="mt-2 rounded-lg border border-slate-700/70 bg-slate-900/60 p-3">
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
                {feedback.message}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-slate-800 bg-slate-900/50 p-4">
          {hasImages && onViewImages && (
            <button
              className="rounded-lg border border-sky-600/50 bg-sky-600/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:border-sky-500 hover:bg-sky-600/20"
              onClick={onViewImages}
            >
              🖼 View Images ({imageCount})
            </button>
          )}
          <button
            type="button"
            className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-sm font-semibold text-slate-300 transition-colors hover:border-slate-600 hover:bg-slate-800 hover:text-slate-200"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

