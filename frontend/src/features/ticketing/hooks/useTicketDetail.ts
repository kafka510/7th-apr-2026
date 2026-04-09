import { useCallback, useEffect, useState } from 'react';

import {
  fetchTicketAttachments,
  fetchTicketComments,
  fetchTicketDetail,
  fetchTicketTimeline,
} from '../api';
import type { TicketAttachment, TicketComment, TicketDetail, TicketTimelineEntry } from '../types';

type UseTicketDetailResult = {
  detail: TicketDetail | null;
  timeline: TicketTimelineEntry[];
  comments: TicketComment[];
  attachments: TicketAttachment[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

export const useTicketDetail = (ticketId: string | null): UseTicketDetailResult => {
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [timeline, setTimeline] = useState<TicketTimelineEntry[]>([]);
  const [comments, setComments] = useState<TicketComment[]>([]);
  const [attachments, setAttachments] = useState<TicketAttachment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!ticketId) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [detailPayload, timelinePayload, commentsPayload, attachmentsPayload] = await Promise.all([
        fetchTicketDetail(ticketId),
        fetchTicketTimeline(ticketId),
        fetchTicketComments(ticketId),
        fetchTicketAttachments(ticketId),
      ]);

      setDetail(detailPayload);
      setTimeline(timelinePayload);
      setComments(commentsPayload);
      setAttachments(attachmentsPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ticket detail');
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    load().catch((err) => {
      console.error('Failed to load ticket detail', err);
    });
  }, [load]);

  return {
    detail,
    timeline,
    comments,
    attachments,
    loading,
    error,
    reload: load,
  };
};

