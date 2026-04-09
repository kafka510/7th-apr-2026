 
import { useEffect } from 'react';

interface Alert {
  type: 'success' | 'error';
  message: string;
}

interface AlertContainerProps {
  alert: Alert | null;
  onClose: () => void;
}

export function AlertContainer({ alert, onClose }: AlertContainerProps) {
  useEffect(() => {
    if (alert) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [alert, onClose]);

  if (!alert) return null;

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-xl border p-3 shadow-lg ${
        alert.type === 'success'
          ? 'border-green-600/50 bg-green-600/20 text-green-200'
          : 'border-red-600/50 bg-red-600/20 text-red-200'
      }`}
      role="alert"
    >
      <div className="flex items-start gap-2">
        <span className="text-lg">
          {alert.type === 'success' ? '✓' : '✕'}
        </span>
        <span className="text-sm font-medium">{alert.message}</span>
      </div>
      <button
        type="button"
        onClick={onClose}
        className={`flex size-6 items-center justify-center rounded-lg transition-colors ${
          alert.type === 'success'
            ? 'hover:bg-green-600/30 hover:text-green-100'
            : 'hover:bg-red-600/30 hover:text-red-100'
        }`}
        aria-label="Close"
      >
        ✕
      </button>
    </div>
  );
}

