/**
 * Data Types Sidebar Component
 */
 
import { useTheme } from '../../../contexts/ThemeContext';

export function DataTypesSidebar() {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const cardBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cardHeaderBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';
  const textSecondary = theme === 'dark' ? '#94a3b8' : '#64748b';
  const listItemBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.3)' : 'transparent';
  const listItemBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)';

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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>📊 Data Types</h5>
      </div>
      <div className="card-body" style={{ color: textPrimary }}>
        <div className="list-group list-group-flush">
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>Yield Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>Monthly yield and performance data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>BESS Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>Battery energy storage system data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>AOC Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>Areas of concern data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>ICE Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>ICE performance data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>IC Budget vs Expected Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>IC Budget vs Expected Generation data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>IC Approved Budget Daily Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>IC Approved Budget Daily data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>Loss Calculation Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>Loss calculation and breakdown data</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>Map Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>Site location and basic information</small>
          </div>
          <div 
            className="list-group-item"
            style={{
              backgroundColor: listItemBg,
              borderColor: listItemBorder,
            }}
          >
            <h6 className="mb-1 font-bold" style={{ color: textPrimary }}>Daily Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>Daily generation, budget, and GII data</small>
          </div>
        </div>
      </div>
    </div>
  );
}

