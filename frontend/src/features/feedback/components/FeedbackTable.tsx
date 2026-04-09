 
import { useTheme } from '../../../contexts/ThemeContext';
import type { Feedback } from '../types';

interface FeedbackTableProps {
  feedbackList: Feedback[];
  onViewMessage: (feedback: Feedback) => void;
  onViewImages: (feedback: Feedback) => void;
  onMarkAttended: (feedbackId: number) => void;
  onDelete: (feedbackId: number, subject: string) => void;
  isSuperuser?: boolean;
}

export function FeedbackTable({
  feedbackList,
  onViewMessage,
  onViewImages,
  onMarkAttended,
  onDelete,
  isSuperuser = false,
}: FeedbackTableProps) {
  const { theme } = useTheme();
  
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const tableRowBg = theme === 'dark' ? 'transparent' : 'transparent';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(248, 250, 252, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowSecondaryText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const linkColor = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const linkHoverColor = theme === 'dark' ? '#93c5fd' : '#0056a3';
  const badgeBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const badgeText = theme === 'dark' ? '#64748b' : '#475569';
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    };
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm" style={{ borderColor: tableBorder }}>
        <thead 
          className="border-b text-xs uppercase tracking-wide"
          style={{
            borderColor: tableBorder,
            backgroundColor: tableHeaderBg,
          }}
        >
          <tr>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Date</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>User</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Email</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Subject</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Message</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Status</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Image</th>
            <th className="px-3 py-2.5" style={{ color: tableHeaderText }}>Actions</th>
          </tr>
        </thead>
        <tbody style={{ borderColor: tableBorder }}>
          {feedbackList.map((feedback) => {
            const { date, time } = formatDate(feedback.created_at);
            const messagePreview = feedback.message.length > 100
              ? feedback.message.substring(0, 100) + '...'
              : feedback.message;
            const hasImages = feedback.images && feedback.images.length > 0;
            const imageCount = feedback.image_count || (feedback.images ? feedback.images.length : 0);

            return (
              <tr 
                key={feedback.id} 
                className="border-b transition-colors"
                style={{
                  borderColor: tableBorder,
                  backgroundColor: tableRowBg,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = tableRowHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = tableRowBg;
                }}
              >
                <td className="px-3 py-2.5">
                  <div className="text-xs" style={{ color: tableRowSecondaryText }}>
                    {date}
                    <br />
                    {time}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="font-semibold" style={{ color: tableRowText }}>{feedback.user.username}</div>
                  {feedback.user.first_name || feedback.user.last_name ? (
                    <div className="text-xs" style={{ color: tableRowSecondaryText }}>
                      {feedback.user.first_name} {feedback.user.last_name}
                    </div>
                  ) : null}
                </td>
                <td className="px-3 py-2.5">
                  <a
                    href={`mailto:${feedback.user_email}`}
                    className="transition-colors hover:underline"
                    style={{ color: linkColor }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = linkHoverColor;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = linkColor;
                    }}
                  >
                    {feedback.user_email}
                  </a>
                </td>
                <td className="px-3 py-2.5">
                  <div className="font-semibold" style={{ color: tableRowText }}>{feedback.subject}</div>
                </td>
                <td className="px-3 py-2.5">
                  <div style={{ color: tableRowText }}>
                    {feedback.message.length > 100 ? (
                      <>
                        <span>{messagePreview}</span>
                        <button
                          type="button"
                          className="ml-1 transition-colors hover:underline"
                          style={{ color: linkColor }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = linkHoverColor;
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = linkColor;
                          }}
                          onClick={() => onViewMessage(feedback)}
                        >
                          Read more
                        </button>
                      </>
                    ) : (
                      feedback.message
                    )}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  {feedback.attended_status === 'attended' ? (
                    <div className="space-y-1">
                      <div 
                        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: theme === 'dark' ? 'rgba(5, 150, 105, 0.2)' : 'rgba(16, 185, 129, 0.1)',
                          color: theme === 'dark' ? '#6ee7b7' : '#059669',
                        }}
                      >
                        ✓ Attended
                      </div>
                      {feedback.attended_at && (
                        <div className="text-xs" style={{ color: tableRowSecondaryText }}>
                          {new Date(feedback.attended_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div 
                      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: theme === 'dark' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.1)',
                        color: theme === 'dark' ? '#fbbf24' : '#d97706',
                      }}
                    >
                      ⏱ Pending
                    </div>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  {hasImages || imageCount > 0 ? (
                    <div className="space-y-1.5">
                      <div 
                        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
                          color: theme === 'dark' ? '#60a5fa' : '#0072ce',
                        }}
                      >
                        🖼 {imageCount} Image{imageCount !== 1 ? 's' : ''}
                      </div>
                      <button
                        className="block rounded-lg border px-2 py-1 text-xs font-medium transition-colors"
                        style={{
                          borderColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)',
                          backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)',
                          color: theme === 'dark' ? '#93c5fd' : '#1e40af',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? '#3b82f6' : '#0072ce';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)';
                        }}
                        onClick={() => onViewImages(feedback)}
                      >
                        👁 View
                      </button>
                    </div>
                  ) : (
                    <div 
                      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: badgeBg,
                        color: badgeText,
                      }}
                    >
                      No Image
                    </div>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-col gap-1">
                    {feedback.attended_status === 'pending' && (
                      <button
                        className="rounded-lg border px-2 py-1 text-xs font-semibold transition-colors"
                        style={{
                          borderColor: theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(5, 150, 105, 0.7)',
                          backgroundColor: theme === 'dark' ? 'rgba(5, 150, 105, 0.2)' : 'rgba(16, 185, 129, 0.1)',
                          color: theme === 'dark' ? '#6ee7b7' : '#059669',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? '#10b981' : '#059669';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(5, 150, 105, 0.3)' : 'rgba(16, 185, 129, 0.15)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(5, 150, 105, 0.7)';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(5, 150, 105, 0.2)' : 'rgba(16, 185, 129, 0.1)';
                        }}
                        onClick={() => onMarkAttended(feedback.id)}
                        title="Mark as Attended and Send Thank You Email"
                      >
                        ✓ Mark Attended
                      </button>
                    )}
                    {hasImages || imageCount > 0 ? (
                      <button
                        className="rounded-lg border px-2 py-1 text-xs font-semibold transition-colors"
                        style={{
                          borderColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)',
                          backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)',
                          color: theme === 'dark' ? '#93c5fd' : '#1e40af',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? '#3b82f6' : '#0072ce';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)';
                        }}
                        onClick={() => onViewImages(feedback)}
                        title="View Images"
                      >
                        🖼
                      </button>
                    ) : null}
                    <button
                      className="rounded-lg border px-2 py-1 text-xs font-semibold transition-colors"
                      style={{
                        borderColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)',
                        backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)',
                        color: theme === 'dark' ? '#93c5fd' : '#1e40af',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = theme === 'dark' ? '#3b82f6' : '#0072ce';
                        e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
                        e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)';
                      }}
                      onClick={() => onViewMessage(feedback)}
                      title="View Full Message"
                    >
                      👁
                    </button>
                    {feedback.attended_status === 'attended' && isSuperuser && (
                      <button
                        className="rounded-lg border px-2 py-1 text-xs font-semibold transition-colors"
                        style={{
                          borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)',
                          backgroundColor: theme === 'dark' ? 'rgba(190, 18, 60, 0.1)' : 'rgba(254, 242, 242, 0.9)',
                          color: theme === 'dark' ? '#fca5a5' : '#dc2626',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? '#f87171' : '#dc2626';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(190, 18, 60, 0.2)' : '#fee2e2';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)';
                          e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(190, 18, 60, 0.1)' : 'rgba(254, 242, 242, 0.9)';
                        }}
                        onClick={() => onDelete(feedback.id, feedback.subject)}
                        title="Delete Feedback (Superuser Only)"
                      >
                        🗑 Delete
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

