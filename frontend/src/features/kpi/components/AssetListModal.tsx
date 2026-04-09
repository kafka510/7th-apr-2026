import { useEffect, useRef } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';

type AssetListModalProps = {
  isOpen: boolean;
  title: string;
  assetNumbers: string[];
  onClose: () => void;
};

export const AssetListModal = ({
  isOpen,
  title,
  assetNumbers,
  onClose,
}: AssetListModalProps) => {
  const { theme } = useTheme();
  const modalRef = useRef<HTMLDivElement>(null);

  const overlayBg = theme === 'dark' ? 'rgba(0, 0, 0, 0.6)' : 'rgba(0, 0, 0, 0.4)';
  const modalBg = theme === 'dark' ? '#0f172a' : '#ffffff';
  const modalBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const headerBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const headerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const titleColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const closeButtonColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const closeButtonHoverBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(241, 245, 249, 0.8)';
  const assetBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(248, 250, 252, 0.8)';
  const assetBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const assetText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const footerBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const footerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const footerText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const noAssetsText = theme === 'dark' ? '#94a3b8' : '#64748b';

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
      style={{ backgroundColor: overlayBg }}
    >
      <div
        ref={modalRef}
        className="relative max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-2xl border shadow-2xl"
        style={{
          borderColor: modalBorder,
          backgroundColor: modalBg,
          boxShadow: theme === 'dark' ? '0 20px 25px -5px rgba(0, 0, 0, 0.7)' : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div 
          className="flex items-center justify-between border-b px-6 py-4"
          style={{
            borderColor: headerBorder,
            backgroundColor: headerBg,
          }}
        >
          <h2 className="text-lg font-semibold" style={{ color: titleColor }}>{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 transition"
            style={{ color: closeButtonColor }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = closeButtonHoverBg;
              e.currentTarget.style.color = theme === 'dark' ? '#ffffff' : '#1a1a1a';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = closeButtonColor;
            }}
            aria-label="Close"
          >
            <svg
              className="size-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-6">
          {assetNumbers.length === 0 ? (
            <p className="text-center" style={{ color: noAssetsText }}>No assets found</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
              {assetNumbers.map((assetNumber) => (
                <div
                  key={assetNumber}
                  className="rounded-lg border px-4 py-2.5 text-sm font-medium transition hover:border-sky-500/50"
                  style={{
                    borderColor: assetBorder,
                    backgroundColor: assetBg,
                    color: assetText,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = theme === 'dark' 
                      ? 'rgba(51, 65, 85, 0.6)' 
                      : 'rgba(241, 245, 249, 0.9)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = assetBg;
                  }}
                >
                  {assetNumber}
                </div>
              ))}
            </div>
          )}
        </div>

        <div 
          className="border-t px-6 py-3"
          style={{
            borderColor: footerBorder,
            backgroundColor: footerBg,
          }}
        >
          <p className="text-xs" style={{ color: footerText }}>
            Total: {assetNumbers.length} asset{assetNumbers.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    </div>
  );
};

