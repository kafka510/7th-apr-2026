 
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
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

  return (
    <nav aria-label="Feedback pagination" className="flex items-center justify-center">
      <div className="flex items-center gap-1">
        {/* First Button */}
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:bg-slate-800/50"
        >
          First
        </button>

        {/* Previous Button */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:bg-slate-800/50"
        >
          Previous
        </button>

        {/* First page if not visible */}
        {startPage > 1 && (
          <>
            <button
              onClick={() => onPageChange(1)}
              className="rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200"
            >
              1
            </button>
            {startPage > 2 && (
              <span className="px-2 text-xs text-slate-500">...</span>
            )}
          </>
        )}

        {/* Page Numbers */}
        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`rounded-lg border px-2.5 py-1 text-xs font-semibold transition-all duration-200 ${
              currentPage === page
                ? 'border-sky-500 bg-sky-600/30 text-sky-200 shadow-md shadow-sky-500/20'
                : 'border-slate-700 bg-slate-800/50 text-slate-300 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            {page}
          </button>
        ))}

        {/* Last page if not visible */}
        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && (
              <span className="px-2 text-xs text-slate-500">...</span>
            )}
            <button
              onClick={() => onPageChange(totalPages)}
              className="rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200"
            >
              {totalPages}
            </button>
          </>
        )}

        {/* Next Button */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:bg-slate-800/50"
        >
          Next
        </button>

        {/* Last Button */}
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-sky-500 hover:bg-slate-800 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:bg-slate-800/50"
        >
          Last
        </button>
      </div>
    </nav>
  );
}

