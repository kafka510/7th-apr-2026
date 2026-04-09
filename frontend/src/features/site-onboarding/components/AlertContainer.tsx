 
import { useEffect } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';

interface Alert {
  id: string;
  type: 'success' | 'danger' | 'warning' | 'info';
  message: string;
}

interface AlertContainerProps {
  alerts: Alert[];
  onRemove: (id: string) => void;
}

export function AlertContainer({ alerts, onRemove }: AlertContainerProps) {
  const { theme } = useTheme();
  
  useEffect(() => {
    // Auto-remove alerts after 5 seconds
    const timers = alerts.map((alert) =>
      setTimeout(() => {
        onRemove(alert.id);
      }, 5000)
    );

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [alerts, onRemove]);

  if (alerts.length === 0) return null;

  const getAlertStyles = (type: string) => {
    switch (type) {
      case 'success':
        return {
          borderColor: theme === 'dark' ? 'rgba(56, 189, 248, 0.5)' : 'rgba(59, 130, 246, 0.5)',
          backgroundColor: theme === 'dark' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(59, 130, 246, 0.1)',
          color: theme === 'dark' ? '#7dd3fc' : '#1e40af',
        };
      case 'danger':
        return {
          borderColor: theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.5)',
          backgroundColor: theme === 'dark' ? 'rgba(248, 113, 113, 0.2)' : 'rgba(239, 68, 68, 0.1)',
          color: theme === 'dark' ? '#fca5a5' : '#dc2626',
        };
      case 'warning':
        return {
          borderColor: theme === 'dark' ? 'rgba(250, 204, 21, 0.5)' : 'rgba(250, 204, 21, 0.5)',
          backgroundColor: theme === 'dark' ? 'rgba(250, 204, 21, 0.2)' : 'rgba(250, 204, 21, 0.1)',
          color: theme === 'dark' ? '#fde047' : '#a16207',
        };
      case 'info':
        return {
          borderColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.5)',
          backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
          color: theme === 'dark' ? '#93c5fd' : '#1e40af',
        };
      default:
        return {
          borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)',
          backgroundColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.1)',
          color: theme === 'dark' ? '#cbd5e1' : '#475569',
        };
    }
  };

  return (
    <div id="alertContainer" className="space-y-2">
      {alerts.map((alert) => {
        const alertStyles = getAlertStyles(alert.type);
        return (
          <div
            key={alert.id}
            className="flex items-center justify-between rounded-xl border px-4 py-3"
            style={alertStyles}
            role="alert"
          >
            <span className="text-sm font-medium">{alert.message}</span>
            <button
              type="button"
              className="ml-4 text-lg font-bold opacity-70 transition hover:opacity-100"
              style={{ color: alertStyles.color }}
              aria-label="Close"
              onClick={() => onRemove(alert.id)}
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}

