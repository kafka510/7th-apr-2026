import { useState } from 'react';

import type { TicketDetail } from '../types';

type TicketSummaryProps = {
  detail: TicketDetail | null;
  loading?: boolean;
};

const SummaryItem = ({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) => (
  <div className="flex items-start justify-between border-b border-slate-100 py-2 last:border-b-0">
    <span className="text-xs font-semibold text-slate-600">{label}:</span>
    <span className="text-xs text-slate-900">{value ?? '—'}</span>
  </div>
);

export const TicketSummary = ({ detail, loading = false }: TicketSummaryProps) => {
  const [expanded, setExpanded] = useState(true);

  // Extract device info from metadata if available
  // Device info is stored in metadata.device_info object
  const deviceInfo = detail?.metadata?.device_info as {
    device_name?: string;
    device_type?: string;
    device_id?: string;
  } | undefined;
  
  const subDeviceInfo = detail?.metadata?.sub_device_info as {
    device_name?: string;
    device_type?: string;
  } | undefined;
  
  const deviceName = deviceInfo?.device_name;
  const deviceType = deviceInfo?.device_type;
  const subDeviceName = subDeviceInfo?.device_name;
  
  // Format device display
  const deviceDisplay = deviceName 
    ? `${deviceType ? `${deviceType} - ` : ''}${deviceName}${subDeviceName ? ` / ${subDeviceName}` : ''}`.trim()
    : '—';

  // Format created date
  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // Format created by
  const formatCreatedBy = () => {
    if (!detail?.created_by) return '—';
    const date = formatDate(detail.created_at);
    return `${date} by ${detail.created_by.name || detail.created_by.username || '—'}`;
  };

  // Format watchers as clickable links
  const watchersDisplay = detail?.watchers && detail.watchers.length > 0
    ? detail.watchers.map((w, idx) => (
        <span key={w?.id || idx}>
          {idx > 0 && ', '}
          <a href={`#user-${w?.id}`} className="text-blue-600 hover:underline">
            {w?.name || w?.username || '—'}
          </a>
        </span>
      ))
    : '—';

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Ticket Summary</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="space-y-1 p-4">
          {loading || !detail ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, index) => (
                <div key={`summary-skeleton-${index}`} className="h-6 animate-pulse rounded border border-slate-200 bg-slate-100"></div>
              ))}
            </div>
          ) : (
            <>
              <SummaryItem label="Category" value={detail.category || '—'} />
              <SummaryItem label="Sub-Category" value={detail.sub_category?.name || '—'} />
              <SummaryItem 
                label="Site" 
                value={detail.asset_name && detail.asset_code 
                  ? `${detail.asset_name} (${detail.asset_code})` 
                  : detail.asset_name || '—'} 
              />
              <SummaryItem label="Device" value={deviceDisplay} />
              <SummaryItem label="Created" value={formatCreatedBy()} />
              <SummaryItem label="Loss Category" value={detail.loss_category || '—'} />
              <div className="flex items-start justify-between border-b border-slate-100 py-2 last:border-b-0">
                <span className="text-xs font-semibold text-slate-600">Watchers:</span>
                <span className="text-xs text-slate-900">{watchersDisplay}</span>
              </div>
              <SummaryItem 
                label="Assigned To" 
                value={detail.assigned_to?.name || detail.assigned_to?.username || '—'} 
              />
              <SummaryItem label="Last Updated" value={formatDate(detail.updated_at)} />
              <SummaryItem
                label="Updated By"
                value={detail.updated_by?.name || detail.updated_by?.username || '—'}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
};

