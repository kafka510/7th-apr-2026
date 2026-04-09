 
import type { UserStats } from '../types';

interface StatisticsCardsProps {
  stats: UserStats;
  onActiveUsersClick?: () => void;
  onSecurityAlertsClick?: () => void;
  onTotalUsersClick?: () => void;
  onSuspiciousActivitiesClick?: () => void;
}

export function StatisticsCards({
  stats,
  onActiveUsersClick,
  onSecurityAlertsClick,
  onTotalUsersClick,
  onSuspiciousActivitiesClick,
}: StatisticsCardsProps) {
  return (
    <div className="row mb-4">
      <div className="col-md-3">
        <div
          className="card mb-3 text-white"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: '10px',
            cursor: onActiveUsersClick ? 'pointer' : 'default',
          }}
          onClick={onActiveUsersClick}
        >
          <div className="card-body">
            <h3 className="mb-0" style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
              {stats.active_users_count}
            </h3>
            <p className="mb-0" style={{ opacity: 0.9 }}>
              Active Users (Last 30 min)
            </p>
            {onActiveUsersClick && (
              <small style={{ opacity: 0.8 }}>Click to view details</small>
            )}
          </div>
        </div>
      </div>
      <div className="col-md-3">
        <div
          className="card mb-3 text-white"
          style={{
            background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%)',
            borderRadius: '10px',
            cursor: onSecurityAlertsClick ? 'pointer' : 'default',
          }}
          onClick={onSecurityAlertsClick}
        >
          <div className="card-body">
            <h3 className="mb-0" style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
              {stats.security_alerts_count}
            </h3>
            <p className="mb-0" style={{ opacity: 0.9 }}>
              Open Security Alerts
            </p>
            {onSecurityAlertsClick && (
              <small style={{ opacity: 0.8 }}>Click to view alerts</small>
            )}
          </div>
        </div>
      </div>
      <div className="col-md-3">
        <div
          className="card mb-3 text-white"
          style={{
            background: 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)',
            borderRadius: '10px',
            cursor: onTotalUsersClick ? 'pointer' : 'default',
          }}
          onClick={onTotalUsersClick}
        >
          <div className="card-body">
            <h3 className="mb-0" style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
              {stats.total_users}
            </h3>
            <p className="mb-0" style={{ opacity: 0.9 }}>
              Total Users
            </p>
            {onTotalUsersClick && (
              <small style={{ opacity: 0.8 }}>Click to view breakdown</small>
            )}
          </div>
        </div>
      </div>
      <div className="col-md-3">
        <div
          className="card mb-3 text-white"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: '10px',
            cursor: onSuspiciousActivitiesClick ? 'pointer' : 'default',
          }}
          onClick={onSuspiciousActivitiesClick}
        >
          <div className="card-body">
            <h3 className="mb-0" style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
              {stats.suspicious_activities_count}
            </h3>
            <p className="mb-0" style={{ opacity: 0.9 }}>
              Suspicious Activities (24h)
            </p>
            {onSuspiciousActivitiesClick && (
              <small style={{ opacity: 0.8 }}>Click to view details</small>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

