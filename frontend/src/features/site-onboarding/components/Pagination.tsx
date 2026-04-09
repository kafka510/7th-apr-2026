 
import { useTheme } from '../../../contexts/ThemeContext';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const pageLinkBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const pageLinkText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const pageLinkBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';
  const pageLinkHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#f8f9fa';
  const pageLinkActiveBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const pageLinkActiveText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const pageLinkDisabledBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.3)' : '#f8f9fa';
  const pageLinkDisabledText = theme === 'dark' ? '#64748b' : '#94a3b8';
  if (totalPages <= 1) return null;

  const pages = [];
  const maxVisible = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  const endPage = Math.min(totalPages, startPage + maxVisible - 1);

  if (endPage - startPage < maxVisible - 1) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    pages.push(i);
  }

  const getPageLinkStyle = (isActive: boolean, isDisabled: boolean) => {
    if (isDisabled) {
      return {
        backgroundColor: pageLinkDisabledBg,
        color: pageLinkDisabledText,
        borderColor: pageLinkBorder,
        cursor: 'not-allowed',
        opacity: 0.6
      };
    }
    if (isActive) {
      return {
        backgroundColor: pageLinkActiveBg,
        color: pageLinkActiveText,
        borderColor: pageLinkBorder,
        fontWeight: '600'
      };
    }
    return {
      backgroundColor: pageLinkBg,
      color: pageLinkText,
      borderColor: pageLinkBorder
    };
  };

  return (
    <nav>
      <ul className="pagination justify-content-center">
        <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
          <button
            className="page-link"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            style={getPageLinkStyle(false, currentPage === 1)}
            onMouseEnter={(e) => {
              if (currentPage !== 1) {
                e.currentTarget.style.backgroundColor = pageLinkHoverBg;
              }
            }}
            onMouseLeave={(e) => {
              if (currentPage !== 1) {
                e.currentTarget.style.backgroundColor = pageLinkBg;
              }
            }}
          >
            Previous
          </button>
        </li>
        {startPage > 1 && (
          <>
            <li className="page-item">
              <button 
                className="page-link" 
                onClick={() => onPageChange(1)}
                style={getPageLinkStyle(false, false)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = pageLinkHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = pageLinkBg;
                }}
              >
                1
              </button>
            </li>
            {startPage > 2 && (
              <li className="page-item disabled">
                <span 
                  className="page-link"
                  style={getPageLinkStyle(false, true)}
                >
                  ...
                </span>
              </li>
            )}
          </>
        )}
        {pages.map((page) => (
          <li key={page} className={`page-item ${currentPage === page ? 'active' : ''}`}>
            <button
              className="page-link"
              onClick={() => onPageChange(page)}
              style={getPageLinkStyle(currentPage === page, false)}
              onMouseEnter={(e) => {
                if (currentPage !== page) {
                  e.currentTarget.style.backgroundColor = pageLinkHoverBg;
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== page) {
                  e.currentTarget.style.backgroundColor = pageLinkBg;
                }
              }}
            >
              {page}
            </button>
          </li>
        ))}
        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && (
              <li className="page-item disabled">
                <span 
                  className="page-link"
                  style={getPageLinkStyle(false, true)}
                >
                  ...
                </span>
              </li>
            )}
            <li className="page-item">
              <button
                className="page-link"
                onClick={() => onPageChange(totalPages)}
                style={getPageLinkStyle(false, false)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = pageLinkHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = pageLinkBg;
                }}
              >
                {totalPages}
              </button>
            </li>
          </>
        )}
        <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
          <button
            className="page-link"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            style={getPageLinkStyle(false, currentPage === totalPages)}
            onMouseEnter={(e) => {
              if (currentPage !== totalPages) {
                e.currentTarget.style.backgroundColor = pageLinkHoverBg;
              }
            }}
            onMouseLeave={(e) => {
              if (currentPage !== totalPages) {
                e.currentTarget.style.backgroundColor = pageLinkBg;
              }
            }}
          >
            Next
          </button>
        </li>
      </ul>
    </nav>
  );
}

