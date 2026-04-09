/**
 * Upload Modes Sidebar Component
 */
 
import { useTheme } from '../../../contexts/ThemeContext';

export function UploadModesSidebar() {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const cardBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cardHeaderBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';

  return (
    <div 
      className="card mb-4"
      style={{
        backgroundColor: cardBg,
        borderColor: cardBorder,
      }}
    >
      <div 
        className="card-header"
        style={{
          backgroundColor: cardHeaderBg,
          borderColor: cardBorder,
        }}
      >
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>📤 Upload Modes</h5>
      </div>
      <div className="card-body" style={{ color: textPrimary }}>
        <h6 className="font-bold" style={{ color: textPrimary }}>📈 Append Mode</h6>
        <p className="small font-medium" style={{ color: textPrimary }}>
          Add new data to existing records. Duplicates are skipped if &quot;Skip duplicates&quot; is enabled.
        </p>

        <h6 className="font-bold" style={{ color: textPrimary }}>🔄 Replace Mode</h6>
        <p className="small font-medium" style={{ color: textPrimary }}>
          Delete existing data in the specified date range and replace with new data.
        </p>

        <h6 className="font-bold" style={{ color: textPrimary }}>⚙️ Advanced Options</h6>
        <ul className="small font-medium" style={{ color: textPrimary }}>
          <li>
            <strong className="font-bold">Skip duplicates:</strong> Prevents duplicate records from being imported
          </li>
          <li>
            <strong className="font-bold">Validate data:</strong> Checks data format and required columns
          </li>
          <li>
            <strong className="font-bold">Batch size:</strong> Number of records processed at once (100-10000)
          </li>
        </ul>
      </div>
    </div>
  );
}

