import { useMemo, useState } from 'react';

import { addTicketComment } from '../api';
import type { TicketAttachment, TicketComment, TicketDetail } from '../types';

type TicketCommentsProps = {
  ticketId: string;
  comments: TicketComment[];
  attachments: TicketAttachment[];
  detail: TicketDetail | null;
  loading?: boolean;
  onCommentAdded?: () => void;
};

type TimelineItem = {
  id: string;
  type: 'comment' | 'attachment';
  timestamp: string;
  comment?: TicketComment;
  attachment?: TicketAttachment;
};

export const TicketComments = ({ ticketId, comments, attachments, detail, loading = false, onCommentAdded }: TicketCommentsProps) => {
  const [commentText, setCommentText] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedImages, setExpandedImages] = useState<Set<number>>(new Set());

  // Check if user can comment (assigned to ticket, can edit, or is watcher)
  const canComment = detail?.permissions?.canComment ?? false;

  // Combine comments and attachments, sorted by timestamp
  const timelineItems = useMemo<TimelineItem[]>(() => {
    const items: TimelineItem[] = [
      ...comments.map((comment) => ({
        id: `comment-${comment.id}`,
        type: 'comment' as const,
        timestamp: comment.created_at,
        comment,
      })),
      ...attachments.map((attachment) => ({
        id: `attachment-${attachment.id}`,
        type: 'attachment' as const,
        timestamp: attachment.created_at,
        attachment,
      })),
    ];

    // Sort by timestamp (newest first)
    return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [comments, attachments]);

  const isImageFile = (fileName: string, fileType?: string | null): boolean => {
    if (fileType) {
      return fileType.startsWith('image/');
    }
    const ext = fileName.toLowerCase().split('.').pop();
    return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext || '');
  };

  const toggleImageExpansion = (attachmentId: number) => {
    setExpandedImages((prev) => {
      const next = new Set(prev);
      if (next.has(attachmentId)) {
        next.delete(attachmentId);
      } else {
        next.add(attachmentId);
      }
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || !canComment) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await addTicketComment(ticketId, commentText.trim(), isInternal);
      setCommentText('');
      setIsInternal(false);
      if (onCommentAdded) {
        onCommentAdded();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add comment');
    } finally {
      setSubmitting(false);
    }
  };

  const [expanded, setExpanded] = useState(true);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Comments</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="p-4">
          {loading ? (
            <p className="text-sm text-slate-500">Loading comments…</p>
          ) : timelineItems.length === 0 ? (
            <p className="text-sm text-slate-500">No comments or attachments yet.</p>
          ) : (
            <ul className="mb-4 space-y-3">
              {timelineItems.map((item) => (
                <li
                  key={item.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"
                >
                  {item.type === 'comment' && item.comment ? (
                    <>
                      <header className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900">{item.comment.user?.name ?? 'System'}</span>
                          {item.comment.is_internal ? (
                            <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                              Internal
                            </span>
                          ) : null}
                        </div>
                        <span className="text-xs text-slate-500">{new Date(item.timestamp).toLocaleString()}</span>
                      </header>
                      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{item.comment.comment}</p>
                    </>
                  ) : item.type === 'attachment' && item.attachment ? (
                    <>
                      <header className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900">
                            📎 {item.attachment.uploaded_by?.name ?? 'Unknown'}
                          </span>
                          <span className="text-xs text-slate-500">uploaded</span>
                        </div>
                        <span className="text-xs text-slate-500">{new Date(item.timestamp).toLocaleString()}</span>
                      </header>
                      <div className="mt-2">
                        <div className="flex items-center gap-2">
                          <a
                            href={item.attachment.file_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-blue-600 hover:text-blue-800"
                          >
                            {item.attachment.file_name}
                          </a>
                          {item.attachment.file_size && (
                            <span className="text-xs text-slate-500">
                              ({(item.attachment.file_size / 1024).toFixed(1)} KB)
                            </span>
                          )}
                        </div>
                        {isImageFile(item.attachment.file_name, item.attachment.file_type) && (
                          <div className="mt-2">
                            <img
                              src={item.attachment.file_url}
                              alt={item.attachment.file_name}
                              className={`cursor-pointer rounded-lg border border-slate-300 transition-all ${
                                expandedImages.has(item.attachment.id)
                                  ? 'max-w-full'
                                  : 'max-h-48 max-w-xs hover:opacity-80'
                              }`}
                              onClick={() => toggleImageExpansion(item.attachment!.id)}
                              onError={(e) => {
                                // Hide image if it fails to load
                                (e.target as HTMLImageElement).style.display = 'none';
                              }}
                            />
                            <p className="mt-1 text-xs text-slate-500">
                              {expandedImages.has(item.attachment.id) ? 'Click to shrink' : 'Click to expand'}
                            </p>
                          </div>
                        )}
                      </div>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          )}

          {canComment && (
            <form onSubmit={handleSubmit} className="space-y-3 border-t border-slate-200 pt-4">
              {error && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  {error}
                </div>
              )}
              <div>
                <textarea
                  id="comment"
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  rows={3}
                  disabled={submitting}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 transition focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-200 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
                  placeholder="Enter your comment..."
                />
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                    disabled={submitting}
                    className="size-4 rounded border-slate-300 text-sky-600 focus:ring-1 focus:ring-sky-200 disabled:cursor-not-allowed"
                  />
                  <span>Internal note</span>
                </label>
                <button
                  type="submit"
                  disabled={submitting || !commentText.trim()}
                  className="ml-auto rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {submitting ? 'Adding...' : 'Add Comment'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
};

