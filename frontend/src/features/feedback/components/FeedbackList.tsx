 
import { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { fetchFeedbackList, markFeedbackAttended, deleteFeedback } from '../api';
import type { Feedback, FeedbackListParams } from '../types';
import { FeedbackFilters } from './FeedbackFilters';
import { FeedbackTable } from './FeedbackTable';
import { MessageModal } from './MessageModal';
import { ImageModal } from './ImageModal';
import { MarkAttendedModal } from './MarkAttendedModal';
import { AlertContainer } from './AlertContainer';
import { Pagination } from './Pagination';

interface FeedbackListProps {
  isSuperuser?: boolean;
}

export function FeedbackList({ isSuperuser = false }: FeedbackListProps) {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const loadingSpinnerBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(203, 213, 225, 0.8)';
  const loadingSpinnerTop = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const loadingText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const [feedbackList, setFeedbackList] = useState<Feedback[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState<FeedbackListParams>({
    status: [],
    search: '',
  });
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null);
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  const [showMarkAttendedModal, setShowMarkAttendedModal] = useState(false);
  const [markAttendedFeedbackId, setMarkAttendedFeedbackId] = useState<number | null>(null);
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadFeedback = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchFeedbackList({
        ...filters,
        page: currentPage,
      });
      setFeedbackList(response.results || []);
      setTotalCount(response.count || 0);
      setTotalPages(response.total_pages || 1);
    } catch (error) {
      console.error('Error loading feedback:', error);
      setAlert({ type: 'error', message: 'Failed to load feedback list' });
    } finally {
      setLoading(false);
    }
  }, [filters, currentPage]);

  useEffect(() => {
    loadFeedback();
  }, [loadFeedback]);

  const handleFilterChange = (newFilters: FeedbackListParams) => {
    setFilters(newFilters);
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handleViewMessage = (feedback: Feedback) => {
    setSelectedFeedback(feedback);
    setShowMessageModal(true);
  };

  const handleViewImages = (feedback: Feedback) => {
    setSelectedFeedback(feedback);
    setShowImageModal(true);
  };

  const handleMarkAttended = (feedbackId: number) => {
    setMarkAttendedFeedbackId(feedbackId);
    setShowMarkAttendedModal(true);
  };

  const handleConfirmMarkAttended = async (adminResponse: string) => {
    if (!markAttendedFeedbackId) return;

    try {
      const result = await markFeedbackAttended(markAttendedFeedbackId, {
        admin_response: adminResponse,
      });

      if (result.success) {
        setAlert({ type: 'success', message: result.message });
        setShowMarkAttendedModal(false);
        setMarkAttendedFeedbackId(null);
        await loadFeedback();
      } else {
        setAlert({ type: 'error', message: result.message || 'Failed to mark feedback as attended' });
      }
    } catch (error) {
      console.error('Error marking feedback as attended:', error);
      setAlert({ type: 'error', message: 'Failed to mark feedback as attended' });
    }
  };

  const handleDelete = async (feedbackId: number, subject: string) => {
    if (!confirm(`Are you sure you want to DELETE this feedback?\n\nSubject: "${subject}"\n\nThis action cannot be undone. Type "DELETE" to confirm:`)) {
      return;
    }

    const userInput = prompt('Type "DELETE" to confirm:');
    if (userInput !== 'DELETE') {
      return;
    }

    try {
      const result = await deleteFeedback(feedbackId);
      if (result.success) {
        setAlert({ type: 'success', message: result.message });
        await loadFeedback();
      } else {
        setAlert({ type: 'error', message: result.message || 'Failed to delete feedback' });
      }
    } catch (error) {
      console.error('Error deleting feedback:', error);
      setAlert({ type: 'error', message: 'Failed to delete feedback' });
    }
  };

  return (
    <div 
      className="flex w-full flex-col"
      style={{
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
        minHeight: '100%',
      }}
    >
      {/* Main Content */}
      <div className="flex h-full flex-col gap-2 overflow-y-auto p-2">
        {/* Header with Count */}
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            <span className="text-xl">💬</span>
            <h2 
              className="text-lg font-bold"
              style={{ color: textColor }}
            >
              User Feedback Management
            </h2>
          </div>
          <div 
            className="text-xs"
            style={{ color: secondaryTextColor }}
          >
            {filters.status.length > 0 || filters.search
              ? `Showing ${feedbackList.length} of ${totalCount} feedback entries`
              : `Total: ${totalCount} feedback entries`}
          </div>
        </div>

        {/* Filters */}
        <div 
          className="relative rounded-xl border p-2 shadow-xl"
          style={{
            borderColor: containerBorder,
            background: containerBg,
            boxShadow: containerShadow,
          }}
        >
          {theme === 'dark' ? (
            <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.12),_transparent_60%)]" />
          ) : (
            <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.06),_transparent_60%)]" />
          )}
          <div className="relative">
          <FeedbackFilters filters={filters} onFilterChange={handleFilterChange} />
          </div>
        </div>

        {/* Alert Container */}
        <AlertContainer alert={alert} onClose={() => setAlert(null)} />

        {/* Content Area */}
        <div 
          className="flex-1 overflow-hidden rounded-xl border shadow-xl"
          style={{
            borderColor: containerBorder,
            background: containerBg,
            boxShadow: containerShadow,
          }}
        >
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <div 
                  className="mb-3 inline-block size-12 animate-spin rounded-full border-4"
                  style={{
                    borderColor: loadingSpinnerBorder,
                    borderTopColor: loadingSpinnerTop,
                  }}
                />
                <p className="text-sm" style={{ color: loadingText }}>Loading feedback...</p>
              </div>
            </div>
          ) : feedbackList.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <div className="mb-4 text-6xl">🔍</div>
                <h5 
                  className="mb-2 text-lg font-semibold"
                  style={{ color: textColor }}
                >
                  No feedback found
                </h5>
                <p 
                  className="text-sm"
                  style={{ color: secondaryTextColor }}
                >
                  {filters.status.length > 0 || filters.search
                    ? 'No feedback entries match your current filters.'
                    : 'When users submit feedback, it will appear here.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex h-full flex-col overflow-hidden">
              <div className="flex-1 overflow-y-auto">
                <FeedbackTable
                  feedbackList={feedbackList}
                  onViewMessage={handleViewMessage}
                  onViewImages={handleViewImages}
                  onMarkAttended={handleMarkAttended}
                  onDelete={handleDelete}
                  isSuperuser={isSuperuser}
                />
              </div>

              {totalPages > 1 && (
                <div 
                  className="border-t p-2"
                  style={{
                    borderColor: containerBorder,
                    backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.9)',
                  }}
                >
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={setCurrentPage}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showMessageModal && selectedFeedback && (
        <MessageModal
          feedback={selectedFeedback}
          onClose={() => {
            setShowMessageModal(false);
            setSelectedFeedback(null);
          }}
          onViewImages={() => {
            setShowMessageModal(false);
            handleViewImages(selectedFeedback);
          }}
        />
      )}

      {showImageModal && selectedFeedback && (
        <ImageModal
          feedback={selectedFeedback}
          onClose={() => {
            setShowImageModal(false);
            setSelectedFeedback(null);
          }}
        />
      )}

      {showMarkAttendedModal && markAttendedFeedbackId && (
        <MarkAttendedModal
          onClose={() => {
            setShowMarkAttendedModal(false);
            setMarkAttendedFeedbackId(null);
          }}
          onConfirm={handleConfirmMarkAttended}
        />
      )}
    </div>
  );
}

