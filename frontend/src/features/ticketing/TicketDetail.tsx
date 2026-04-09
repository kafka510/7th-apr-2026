import { useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { changeTicketStatus, deleteTicket } from './api';
import { TicketActions } from './components/TicketActions';
import { TicketAttachments } from './components/TicketAttachments';
import { TicketBreakdownAnalytics } from './components/TicketBreakdownAnalytics';
import { TicketComments } from './components/TicketComments';
import { TicketSummary } from './components/TicketSummary';
import { TicketResources } from './components/TicketResources';
import { TicketTimeline } from './components/TicketTimeline';
import type { TicketDetail as TicketDetailType } from './types';
import { useTicketDetail } from './hooks/useTicketDetail';

type TicketDetailProps = {
  ticketId: string | null;
};

const Header = ({
  detail,
  loading,
  canDelete,
  canEdit,
  onDelete,
  onClose,
  deleting,
  closing,
}: {
  detail: TicketDetailType | null;
  loading: boolean;
  canDelete: boolean;
  canEdit: boolean;
  onDelete: () => void;
  onClose: () => void;
  deleting: boolean;
  closing: boolean;
}) => {
  const { theme } = useTheme();
  
  const getStatusColor = (status: string | null | undefined) => {
    const baseBorder = theme === 'dark' ? 'rgba(203, 213, 225, 0.5)' : 'rgba(203, 213, 225, 0.8)';
    switch (status) {
      case 'raised':
        return theme === 'dark' 
          ? { bg: 'rgba(59, 130, 246, 0.2)', text: '#93c5fd', border: 'rgba(59, 130, 246, 0.5)' }
          : { bg: '#dbeafe', text: '#1e40af', border: '#bfdbfe' };
      case 'in_progress':
        return theme === 'dark'
          ? { bg: 'rgba(245, 158, 11, 0.2)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.5)' }
          : { bg: '#fef3c7', text: '#92400e', border: '#fde68a' };
      case 'closed':
        return theme === 'dark'
          ? { bg: 'rgba(16, 185, 129, 0.2)', text: '#6ee7b7', border: 'rgba(16, 185, 129, 0.5)' }
          : { bg: '#d1fae5', text: '#065f46', border: '#a7f3d0' };
      case 'cancelled':
        return theme === 'dark'
          ? { bg: 'rgba(239, 68, 68, 0.2)', text: '#fca5a5', border: 'rgba(239, 68, 68, 0.5)' }
          : { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' };
      default:
        return theme === 'dark'
          ? { bg: 'rgba(51, 65, 85, 0.3)', text: '#cbd5e1', border: baseBorder }
          : { bg: '#f1f5f9', text: '#475569', border: baseBorder };
    }
  };

  const getPriorityColor = (priority: string | null | undefined) => {
    const baseBorder = theme === 'dark' ? 'rgba(203, 213, 225, 0.5)' : 'rgba(203, 213, 225, 0.8)';
    switch (priority) {
      case 'critical':
        return theme === 'dark'
          ? { bg: 'rgba(239, 68, 68, 0.2)', text: '#fca5a5', border: 'rgba(239, 68, 68, 0.5)' }
          : { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' };
      case 'high':
        return theme === 'dark'
          ? { bg: 'rgba(249, 115, 22, 0.2)', text: '#fb923c', border: 'rgba(249, 115, 22, 0.5)' }
          : { bg: '#fed7aa', text: '#9a3412', border: '#fdba74' };
      case 'medium':
        return theme === 'dark'
          ? { bg: 'rgba(245, 158, 11, 0.2)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.5)' }
          : { bg: '#fef3c7', text: '#92400e', border: '#fde68a' };
      default:
        return theme === 'dark'
          ? { bg: 'rgba(51, 65, 85, 0.3)', text: '#cbd5e1', border: baseBorder }
          : { bg: '#f1f5f9', text: '#475569', border: baseBorder };
    }
  };

  const headerBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.9)' : '#ffffff';
  const headerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#f8fafc';
  const buttonHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';

  return (
    <header 
      className="border-b"
      style={{
        borderColor: headerBorder,
        backgroundColor: headerBg,
      }}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-6 py-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-4">
            <a
              href="/tickets/"
              className="rounded-lg border px-3 py-1.5 text-sm font-semibold transition"
              style={{
                borderColor: buttonBorder,
                backgroundColor: buttonBg,
                color: buttonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = buttonHoverBorder;
                e.currentTarget.style.backgroundColor = buttonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.backgroundColor = buttonBg;
              }}
            >
              ← Back
            </a>
            <div>
              <h1 
                className="text-xl font-semibold"
                style={{ color: textColor }}
              >
                {detail?.ticket_number ?? '—'} {detail?.title ?? ''}
                {detail?.category && (
                  <span 
                    className="ml-2 text-sm font-normal"
                    style={{ color: secondaryTextColor }}
                  >
                    • {detail.category}
                  </span>
                )}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {detail?.status && (
              <span 
                className="rounded-full border px-3 py-1 text-xs font-semibold"
                style={{
                  backgroundColor: getStatusColor(detail.status).bg,
                  color: getStatusColor(detail.status).text,
                  borderColor: getStatusColor(detail.status).border,
                }}
              >
                {detail.status_display}
              </span>
            )}
            {detail?.priority && (
              <span 
                className="rounded-full border px-3 py-1 text-xs font-semibold"
                style={{
                  backgroundColor: getPriorityColor(detail.priority).bg,
                  color: getPriorityColor(detail.priority).text,
                  borderColor: getPriorityColor(detail.priority).border,
                }}
              >
                {detail.priority_display}
              </span>
            )}
            {canEdit && (
              <a
                href={`/tickets/${detail?.id}/edit/`}
                className="rounded-lg border px-3 py-1.5 text-sm font-semibold transition"
                style={{
                  borderColor: buttonBorder,
                  backgroundColor: buttonBg,
                  color: buttonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = buttonHoverBorder;
                  e.currentTarget.style.backgroundColor = buttonHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = buttonBorder;
                  e.currentTarget.style.backgroundColor = buttonBg;
                }}
              >
                Edit
              </a>
            )}
            {detail?.status !== 'closed' && detail?.status !== 'cancelled' && (
              <button
                type="button"
                onClick={onClose}
                disabled={loading || closing}
                className="rounded-lg border px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  borderColor: theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(5, 150, 105, 0.7)',
                  backgroundColor: theme === 'dark' ? 'rgba(5, 150, 105, 0.1)' : '#ffffff',
                  color: theme === 'dark' ? '#6ee7b7' : '#059669',
                }}
                onMouseEnter={(e) => {
                  if (!loading && !closing) {
                    e.currentTarget.style.borderColor = theme === 'dark' ? '#10b981' : '#059669';
                    e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(5, 150, 105, 0.2)' : '#f0fdf4';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!loading && !closing) {
                    e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(5, 150, 105, 0.7)';
                    e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(5, 150, 105, 0.1)' : '#ffffff';
                  }
                }}
              >
                {closing ? 'Closing…' : '✓ Close'}
              </button>
            )}
            {canDelete && (
              <button
                type="button"
                onClick={onDelete}
                disabled={loading || deleting}
                className="rounded-lg border px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)',
                  backgroundColor: theme === 'dark' ? 'rgba(190, 18, 60, 0.1)' : '#ffffff',
                  color: theme === 'dark' ? '#fca5a5' : '#dc2626',
                }}
                onMouseEnter={(e) => {
                  if (!loading && !deleting) {
                    e.currentTarget.style.borderColor = theme === 'dark' ? '#f87171' : '#dc2626';
                    e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(190, 18, 60, 0.2)' : '#fee2e2';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!loading && !deleting) {
                    e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)';
                    e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(190, 18, 60, 0.1)' : '#ffffff';
                  }
                }}
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

type TabButtonProps = {
  label: string;
  isActive: boolean;
  onClick: () => void;
};

const TabButton = ({ label, isActive, onClick }: TabButtonProps) => {
  const { theme } = useTheme();
  const activeBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const activeText = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const inactiveText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const inactiveHoverText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  
  return (
  <button
    type="button"
    onClick={onClick}
      className="border-b-2 px-4 py-2 text-sm font-semibold transition-colors"
      style={{
        borderBottomColor: isActive ? activeBorder : 'transparent',
        color: isActive ? activeText : inactiveText,
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.color = inactiveHoverText;
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.color = inactiveText;
        }
      }}
  >
    {label}
  </button>
);
};

const TicketDetail = ({ ticketId }: TicketDetailProps) => {
  const { detail, timeline, comments, attachments, loading, error, reload } = useTicketDetail(ticketId);
  const [deleting, setDeleting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  const handleDelete = async () => {
    if (!ticketId || !detail?.permissions?.canDelete) {
      return;
    }

    if (!window.confirm(`Are you sure you want to delete ticket ${detail.ticket_number}? This action cannot be undone.`)) {
      return;
    }

    setDeleting(true);
    try {
      await deleteTicket(ticketId);
      window.location.href = '/tickets/';
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete ticket');
      setDeleting(false);
    }
  };

  const handleClose = async () => {
    if (!ticketId || !detail || detail.status === 'closed' || detail.status === 'cancelled') {
      return;
    }

    if (!window.confirm('Are you sure you want to close this ticket?')) {
      return;
    }

    setClosing(true);
    try {
      await changeTicketStatus(ticketId, 'closed');
      reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to close ticket');
    } finally {
      setClosing(false);
    }
  };

  const { theme } = useTheme();
  const mainBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)' 
    : '#f1f5f9';
  const tabBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.9)' : '#ffffff';
  const tabBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fef2f2';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : '#fecaca';
  const errorText = theme === 'dark' ? '#fca5a5' : '#991b1b';

  return (
    <div 
      className="min-h-screen"
      style={{
        background: mainBg,
        color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
        transition: 'background 0.3s ease, color 0.3s ease',
      }}
    >
      <Header
        detail={detail}
        loading={loading}
        canDelete={detail?.permissions?.canDelete ?? false}
        canEdit={detail?.permissions?.canEdit ?? false}
        onDelete={handleDelete}
        onClose={handleClose}
        deleting={deleting}
        closing={closing}
      />

      <main className="mx-auto max-w-7xl px-6 py-4">
        {error ? (
          <div 
            className="mb-4 rounded-xl border p-4 text-sm shadow-sm"
            style={{
              borderColor: errorBorder,
              backgroundColor: errorBg,
              color: errorText,
            }}
          >
            Failed to load ticket: {error}
          </div>
        ) : null}

        {/* Tab Navigation */}
        <div 
          className="mb-4 border-b"
          style={{
            borderColor: tabBorder,
            backgroundColor: tabBg,
          }}
        >
          <div className="flex gap-1">
            <TabButton
              label="Summary & Description"
              isActive={activeTab === 'summary'}
              onClick={() => setActiveTab('summary')}
            />
            <TabButton
              label="Breakdown & Analytics Details"
              isActive={activeTab === 'breakdown'}
              onClick={() => setActiveTab('breakdown')}
            />
            <TabButton
              label="Materials & Manpower"
              isActive={activeTab === 'resources'}
              onClick={() => setActiveTab('resources')}
            />
            <TabButton
              label="Comments & Attachments"
              isActive={activeTab === 'comments'}
              onClick={() => setActiveTab('comments')}
            />
          </div>
        </div>

        {/* Tab Content */}
        <div>
          {/* Tab 1: Summary & Description */}
          {activeTab === 'summary' && (
            <div className="grid gap-4 lg:grid-cols-3">
              {/* Left Side - Summary & Description */}
              <div className="lg:col-span-2">
                <div className="flex flex-col gap-4">
                  <TicketSummary detail={detail} loading={loading} />
                  {detail?.description && (
                    <div 
                      className="rounded-xl border shadow-sm"
                      style={{
                        borderColor: containerBorder,
                        backgroundColor: containerBg,
                        boxShadow: containerShadow,
                      }}
                    >
                      <div 
                        className="border-b px-4 py-2"
                        style={{
                          borderColor: tabBorder,
                          backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)',
                        }}
                      >
                        <h3 
                          className="text-sm font-semibold"
                          style={{ color: textColor }}
                        >
                          Description
                        </h3>
                      </div>
                      <div className="p-4">
                        <p 
                          className="whitespace-pre-wrap text-sm"
                          style={{ color: theme === 'dark' ? '#cbd5e1' : '#475569' }}
                        >
                          {detail.description}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Sidebar - Actions (Only in first tab) */}
              <div className="lg:col-span-1">
                <TicketActions ticketId={ticketId || ''} detail={detail} onUpdate={reload} />
              </div>
            </div>
          )}

          {/* Tab 2: Breakdown & Analytics Details */}
          {activeTab === 'breakdown' && (
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Left Side - Breakdown & Analytics Details */}
              <div>
                <TicketBreakdownAnalytics ticketId={ticketId || ''} detail={detail} onUpdate={reload} />
              </div>

              {/* Right Side - Activity Timeline */}
              <div>
                <TicketTimeline timeline={timeline} loading={loading} />
              </div>
            </div>
          )}

          {/* Tab 3: Materials & Manpower */}
          {activeTab === 'resources' && (
            <div>
              {ticketId && detail ? (
                <TicketResources
                  ticketId={ticketId}
                  materials={detail.materials}
                  manpower={detail.manpower}
                  canEdit={detail.permissions?.canEdit ?? false}
                  canDelete={detail.permissions?.canDelete ?? false}
                  onUpdate={reload}
                />
              ) : (
                <div 
                  className="rounded-xl border p-4 text-sm"
                  style={{
                    borderColor: containerBorder,
                    backgroundColor: containerBg,
                    color: secondaryTextColor,
                  }}
                >
                  Loading ticket details...
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Comments & Attachments */}
          {activeTab === 'comments' && (
            <div className="flex flex-col gap-4">
              <TicketComments
                ticketId={ticketId || ''}
                comments={comments}
                attachments={attachments}
                detail={detail}
                loading={loading}
                onCommentAdded={reload}
              />
              <TicketAttachments ticketId={ticketId || ''} attachments={attachments} loading={loading} onUpdate={reload} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default TicketDetail;


