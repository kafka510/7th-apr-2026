/**
 * Tips Sidebar Component
 */
 
import { useTheme } from '../../../contexts/ThemeContext';

export function TipsSidebar() {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const cardBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cardHeaderBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';
  const successBg = theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)';
  const successBorder = theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(16, 185, 129, 0.3)';
  const successText = theme === 'dark' ? '#6ee7b7' : '#059669';

  return (
    <div 
      className="card"
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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>💡 Tips</h5>
      </div>
      <div className="card-body" style={{ color: textPrimary }}>
        <ul className="small font-medium" style={{ color: textPrimary }}>
          <li>Use Excel to prepare your CSV files</li>
          <li>Ensure date formats are consistent (YYYY-MM-DD)</li>
          <li>Check for empty cells in required columns</li>
          <li>Use the preview feature to verify data before upload</li>
          <li>Start with small files to test the format</li>
          <li>Backup your data before large updates</li>
          <li>
            <strong className="font-bold">Download templates</strong> to ensure correct format
          </li>
        </ul>

        <div 
          className="alert alert-success mt-3"
          style={{
            backgroundColor: successBg,
            borderColor: successBorder,
            color: successText,
          }}
        >
          <h6 className="font-bold" style={{ color: successText }}>🆕 Recent Improvements:</h6>
          <ul className="mb-0 font-medium" style={{ color: successText }}>
            <li>
              <strong className="font-bold">Progress Indicators:</strong> See real-time upload progress with spinner and progress bar
            </li>
            <li>
              <strong className="font-bold">Toast Notifications:</strong> Get immediate feedback on upload success/failure
            </li>
            <li>
              <strong className="font-bold">Upload History:</strong> Track all your uploads with detailed information
            </li>
            <li>
              <strong className="font-bold">Enhanced Error Handling:</strong> Better error messages and validation
            </li>
            <li>
              <strong className="font-bold">Auto-dismissing Messages:</strong> Alerts automatically disappear after 5 seconds
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

