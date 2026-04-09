 
import type { SuspiciousActivity } from '../types';

interface SuspiciousActivitiesProps {
  activities: SuspiciousActivity[];
}

export function SuspiciousActivities({ activities }: SuspiciousActivitiesProps) {
  if (!activities || activities.length === 0) {
    return (
      <div className="mb-4 rounded bg-white p-4 shadow-sm">
        <h4 className="mb-3">Recent Suspicious Activities</h4>
        <p className="text-muted mb-0">No suspicious activities in the last 24 hours.</p>
      </div>
    );
  }

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getActionDisplay = (action: string): string => {
    // Convert action to display format
    return action
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="mb-4 rounded bg-white p-4 shadow-sm">
      <h4 className="mb-3">Recent Suspicious Activities</h4>
      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="border-start border-warning bg-warning/10 mb-2 rounded border-4 p-2"
          >
            <strong>{getActionDisplay(activity.action)}</strong>
            <br />
            <small>
              {activity.user?.username || 'Anonymous'} - {activity.ip_address}
            </small>
            <br />
            <small>{formatTimestamp(activity.timestamp)}</small>
            <br />
            <small className="text-muted">{activity.resource}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

