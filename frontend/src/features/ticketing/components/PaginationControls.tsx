import { useTheme } from '../../../contexts/ThemeContext';

type PaginationControlsProps = {
  page: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
};

export const PaginationControls = ({
  page,
  totalPages,
  totalCount,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: PaginationControlsProps) => {
  const { theme } = useTheme();
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const textColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const highlightColor = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const selectBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const selectBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const selectText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const selectHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';
  const selectFocusBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';
  const buttonHoverText = theme === 'dark' ? '#93c5fd' : '#0072ce';

  return (
    <div 
      className="flex flex-col gap-2 rounded-xl border px-3 py-2 text-xs shadow-xl md:flex-row md:items-center md:justify-between"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
        color: textColor,
      }}
    >
      <div>
        Showing page{' '}
        <span className="font-semibold" style={{ color: highlightColor }}>
          {page} / {totalPages}
        </span>{' '}
        · {totalCount} total tickets
      </div>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1">
          <span 
            className="text-[10px] uppercase tracking-wide"
            style={{ color: labelColor }}
          >
            Rows per page
          </span>
          <select
            value={pageSize}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            className="rounded-lg border py-0.5 pl-1.5 pr-6 text-xs shadow-inner transition focus:outline-none focus:ring-1"
            style={{ 
              paddingRight: '1.75rem',
              borderColor: selectBorder,
              backgroundColor: selectBg,
              color: selectText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = selectHoverBorder;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = selectBorder;
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = selectFocusBorder;
              e.currentTarget.style.boxShadow = theme === 'dark' 
                ? '0 0 0 1px rgba(59, 130, 246, 0.3)' 
                : '0 0 0 1px rgba(0, 114, 206, 0.2)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = selectBorder;
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {[10, 20, 30, 50].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-1.5">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(1)}
            className="rounded-lg border px-2 py-0.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              if (page > 1) {
                e.currentTarget.style.borderColor = buttonHoverBorder;
                e.currentTarget.style.color = buttonHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (page > 1) {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.color = buttonText;
              }
            }}
          >
            First
          </button>
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(Math.max(1, page - 1))}
            className="rounded-lg border px-2 py-0.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              if (page > 1) {
                e.currentTarget.style.borderColor = buttonHoverBorder;
                e.currentTarget.style.color = buttonHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (page > 1) {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.color = buttonText;
              }
            }}
          >
            Previous
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            className="rounded-lg border px-2 py-0.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              if (page < totalPages) {
                e.currentTarget.style.borderColor = buttonHoverBorder;
                e.currentTarget.style.color = buttonHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (page < totalPages) {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.color = buttonText;
              }
            }}
          >
            Next
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(totalPages)}
            className="rounded-lg border px-2 py-0.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              if (page < totalPages) {
                e.currentTarget.style.borderColor = buttonHoverBorder;
                e.currentTarget.style.color = buttonHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (page < totalPages) {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.color = buttonText;
              }
            }}
          >
            Last
          </button>
        </div>
      </div>
    </div>
  );
};


