 
import { useState, useEffect } from 'react';
import { fetchFeedbackImages } from '../api';
import type { Feedback } from '../types';

interface ImageModalProps {
  feedback: Feedback;
  onClose: () => void;
}

export function ImageModal({ feedback, onClose }: ImageModalProps) {
  const [images, setImages] = useState<Array<{ id: number; url: string; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadImages = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchFeedbackImages(feedback.id);
        if (result.success) {
          setImages(result.images || []);
        } else {
          setError('Failed to load images');
        }
      } catch (err) {
        console.error('Error loading images:', err);
        setError('Failed to load images');
      } finally {
        setLoading(false);
      }
    };

    loadImages();
  }, [feedback.id]);

  const imageCount = images.length || feedback.image_count || 0;

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative mx-4 w-full max-w-5xl rounded-xl border border-slate-800/80 bg-gradient-to-br from-slate-900/95 to-slate-800/95 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-gradient-to-r from-sky-600/10 to-purple-600/10 p-4">
          <h5 className="text-lg font-bold text-sky-400">
            🖼 Images from {feedback.user.username} ({imageCount} image{imageCount !== 1 ? 's' : ''})
          </h5>
          <button
            type="button"
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[70vh] overflow-y-auto p-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="mb-3 size-12 animate-spin rounded-full border-4 border-sky-500/20 border-t-sky-500"></div>
              <p className="text-sm text-slate-400">Loading images...</p>
            </div>
          ) : error ? (
            <div className="flex items-start gap-3 rounded-xl border border-red-600/50 bg-red-600/20 p-4 text-red-200">
              <span className="text-lg">⚠️</span>
              <span className="text-sm font-medium">{error}</span>
            </div>
          ) : images.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="mb-3 text-5xl">🖼️</div>
              <p className="text-sm text-slate-400">No images found for this feedback.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {images.map((image, index) => (
                <div
                  key={image.id}
                  className="overflow-hidden rounded-lg border border-slate-700/70 bg-slate-800/50 shadow-md"
                >
                  <img
                    src={image.url}
                    className="h-48 w-full object-cover"
                    alt={`Feedback Image ${index + 1}`}
                    loading="lazy"
                  />
                  <div className="space-y-2 p-3">
                    <a
                      href={image.url}
                      className="block rounded-lg border border-sky-600/50 bg-sky-600/10 px-3 py-2 text-center text-xs font-semibold text-sky-300 transition-colors hover:border-sky-500 hover:bg-sky-600/20"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      🔍 View Full Size
                    </a>
                    <a
                      href={image.url}
                      className="block rounded-lg border border-green-600/50 bg-green-600/10 px-3 py-2 text-center text-xs font-semibold text-green-300 transition-colors hover:border-green-500 hover:bg-green-600/20"
                      download
                      title="Download Image"
                    >
                      📥 Download
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-slate-800 bg-slate-900/50 p-4">
          <button
            type="button"
            className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-sm font-semibold text-slate-300 transition-colors hover:border-slate-600 hover:bg-slate-800 hover:text-slate-200"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

