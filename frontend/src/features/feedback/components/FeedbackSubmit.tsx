 
import { useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { submitFeedback } from '../api';
import type { FeedbackSubmitPayload } from '../types';

interface FeedbackSubmitProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function FeedbackSubmit({ onSuccess, onCancel }: FeedbackSubmitProps) {
  const { theme } = useTheme();
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [images, setImages] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const inputPlaceholder = theme === 'dark' ? '#64748b' : '#94a3b8';
  const inputFocusBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const labelColor = theme === 'dark' ? '#cbd5e1' : '#475569';
  const submitButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.8)' : '#0072ce';
  const submitButtonHoverBg = theme === 'dark' ? 'rgba(37, 99, 235, 0.9)' : '#0056a3';
  const cancelButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const cancelButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cancelButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const cancelButtonHoverBorder = theme === 'dark' ? 'rgba(148, 163, 184, 0.7)' : '#94a3b8';
  const dragZoneBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.9)';
  const dragZoneBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.5)';
  const dragZoneHoverBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const successAlertBg = theme === 'dark' ? 'rgba(5, 150, 105, 0.2)' : '#dcfce7';
  const successAlertBorder = theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : '#86efac';
  const successAlertText = theme === 'dark' ? '#6ee7b7' : '#16a34a';
  const errorAlertBg = theme === 'dark' ? 'rgba(190, 18, 60, 0.2)' : '#fee2e2';
  const errorAlertBorder = theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : '#fca5a5';
  const errorAlertText = theme === 'dark' ? '#fca5a5' : '#dc2626';

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter((file) => file.type.startsWith('image/'));
    setImages((prev) => [...prev, ...imageFiles]);
    updateImagePreviews([...images, ...imageFiles]);
  };

  const updateImagePreviews = (files: File[]) => {
    const previews: string[] = [];
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result) {
          previews.push(e.target.result as string);
          if (previews.length === files.length) {
            setImagePreviews(previews);
          }
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const handleRemoveImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index);
    setImages(newImages);
    const newPreviews = imagePreviews.filter((_, i) => i !== index);
    setImagePreviews(newPreviews);
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const items = Array.from(e.clipboardData.items);
    const imageFiles: File[] = [];

    items.forEach((item) => {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) {
          imageFiles.push(file);
        }
      }
    });

    if (imageFiles.length > 0) {
      setImages((prev) => [...prev, ...imageFiles]);
      updateImagePreviews([...images, ...imageFiles]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    const imageFiles = files.filter((file) => file.type.startsWith('image/'));
    setImages((prev) => [...prev, ...imageFiles]);
    updateImagePreviews([...images, ...imageFiles]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!subject.trim() || !message.trim()) {
      setAlert({ type: 'error', message: 'Subject and message are required' });
      return;
    }

    setLoading(true);
    setAlert(null);

    try {
      const payload: FeedbackSubmitPayload = {
        subject: subject.trim(),
        message: message.trim(),
        images: images.length > 0 ? images : undefined,
      };

      const result = await submitFeedback(payload);

      if (result.success || result.message) {
        setAlert({ type: 'success', message: result.message || 'Feedback submitted successfully!' });
        setSubject('');
        setMessage('');
        setImages([]);
        setImagePreviews([]);

        // Clear file input
        const fileInput = document.getElementById('feedback-images') as HTMLInputElement;
        if (fileInput) {
          fileInput.value = '';
        }

        if (result.close_modal && onSuccess) {
          setTimeout(() => {
            onSuccess();
          }, 2000);
        }
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to submit feedback',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="flex w-full flex-col"
      style={{
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
        minHeight: '100%',
      }}
    >
      {/* Main Content */}
      <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
        <div className="mx-auto w-full max-w-3xl">
          {/* Header */}
          <div className="mb-4 text-center">
            <div className="mb-2 flex items-center justify-center gap-2">
              <span className="text-3xl">💬</span>
              <h2 
                className="text-2xl font-bold"
                style={{ color: textColor }}
              >
                Submit Feedback
              </h2>
            </div>
            <p 
              className="text-sm"
              style={{ color: secondaryTextColor }}
            >
              We value your feedback! Please share your thoughts, suggestions, or report any issues you&apos;ve encountered.
            </p>
          </div>

          {/* Alert */}
          {alert && (
            <div
              className="mb-4 flex items-start justify-between gap-3 rounded-xl border p-3 shadow-lg"
              style={{
                borderColor: alert.type === 'success' ? successAlertBorder : errorAlertBorder,
                backgroundColor: alert.type === 'success' ? successAlertBg : errorAlertBg,
                color: alert.type === 'success' ? successAlertText : errorAlertText,
              }}
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
                onClick={() => setAlert(null)}
                className="flex size-6 items-center justify-center rounded-lg transition-colors"
                style={{
                  color: alert.type === 'success' ? successAlertText : errorAlertText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = alert.type === 'success' 
                    ? (theme === 'dark' ? 'rgba(5, 150, 105, 0.3)' : 'rgba(16, 185, 129, 0.2)')
                    : (theme === 'dark' ? 'rgba(190, 18, 60, 0.3)' : 'rgba(239, 68, 68, 0.2)');
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
                aria-label="Close"
              >
                ✕
              </button>
            </div>
          )}

          {/* Form Card */}
          <div 
            className="rounded-xl border p-6 shadow-xl"
            style={{
              borderColor: containerBorder,
              background: containerBg,
              boxShadow: containerShadow,
            }}
          >
            <form onSubmit={handleSubmit} onPaste={handlePaste} className="space-y-4">
              {/* Subject Field */}
              <div>
                <label 
                  htmlFor="subject" 
                  className="mb-1.5 flex items-center gap-2 text-sm font-semibold"
                  style={{ color: labelColor }}
                >
                  📝 Subject <span style={{ color: theme === 'dark' ? '#f87171' : '#dc2626' }}>*</span>
                </label>
                <input
                  type="text"
                  id="subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Enter feedback subject"
                  required
                  className="w-full rounded-lg border px-3 py-2 text-sm shadow-inner transition-all duration-200 focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                    boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                  }}
                  onMouseEnter={(e) => {
                    if (document.activeElement !== e.currentTarget) {
                      e.currentTarget.style.borderColor = inputFocusBorder;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (document.activeElement !== e.currentTarget) {
                      e.currentTarget.style.borderColor = inputBorder;
                    }
                  }}
                />
                <style>{`
                  #subject::placeholder {
                    color: ${inputPlaceholder};
                  }
                  #subject:focus {
                    border-color: ${inputFocusBorder};
                    box-shadow: 0 0 0 2px ${theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(0, 114, 206, 0.2)'};
                  }
                `}</style>
              </div>

              {/* Message Field */}
              <div>
                <label 
                  htmlFor="message" 
                  className="mb-1.5 flex items-center gap-2 text-sm font-semibold"
                  style={{ color: labelColor }}
                >
                  💭 Feedback Message <span style={{ color: theme === 'dark' ? '#f87171' : '#dc2626' }}>*</span>
                </label>
                <textarea
                  id="message"
                  rows={5}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Enter your feedback message"
                  required
                  className="w-full rounded-lg border px-3 py-2 text-sm shadow-inner transition-all duration-200 focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                    boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                  }}
                  onMouseEnter={(e) => {
                    if (document.activeElement !== e.currentTarget) {
                      e.currentTarget.style.borderColor = inputFocusBorder;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (document.activeElement !== e.currentTarget) {
                      e.currentTarget.style.borderColor = inputBorder;
                    }
                  }}
                />
                <style>{`
                  #message::placeholder {
                    color: ${inputPlaceholder};
                  }
                  #message:focus {
                    border-color: ${inputFocusBorder};
                    box-shadow: 0 0 0 2px ${theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(0, 114, 206, 0.2)'};
                  }
                `}</style>
              </div>

              {/* Images Upload Field */}
              <div>
                <label 
                  htmlFor="feedback-images" 
                  className="mb-1.5 flex items-center gap-2 text-sm font-semibold"
                  style={{ color: labelColor }}
                >
                  🖼 Upload Images (Optional)
                </label>
                <input
                  type="file"
                  id="feedback-images"
                  accept="image/*"
                  multiple
                  onChange={handleImageChange}
                  className="w-full rounded-lg border px-3 py-2 text-sm shadow-inner transition-all duration-200 file:mr-3 file:rounded-md file:border-0 file:px-3 file:py-1 file:text-xs file:font-semibold file:transition-colors"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                    boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
                  }}
                />
                <style>{`
                  #feedback-images::file-selector-button {
                    background-color: ${theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)'};
                    color: ${theme === 'dark' ? '#93c5fd' : '#1e40af'};
                  }
                  #feedback-images::file-selector-button:hover {
                    background-color: ${theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)'};
                  }
                `}</style>
                <div 
                  className="mt-1.5 text-xs"
                  style={{ color: secondaryTextColor }}
                >
                  ℹ️ You can attach multiple screenshots or images to help us understand your feedback better. 
                  Supported formats: JPG, PNG, GIF (Max size: 5MB each)
                </div>

                {/* Image Previews */}
                {imagePreviews.length > 0 && (
                  <div className="mt-3">
                    <h6 
                      className="mb-2 text-sm font-semibold"
                      style={{ color: labelColor }}
                    >
                      Selected Images:
                    </h6>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                      {imagePreviews.map((preview, index) => (
                        <div
                          key={index}
                          className="overflow-hidden rounded-lg border shadow-md"
                          style={{
                            borderColor: inputBorder,
                            backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.9)',
                          }}
                        >
                          <img
                            src={preview}
                            className="h-32 w-full object-cover"
                            alt={`Preview ${index + 1}`}
                          />
                          <div className="space-y-1 p-2">
                            <div 
                              className="truncate text-xs"
                              style={{ color: secondaryTextColor }}
                            >
                              {images[index].name}
                            </div>
                            <div 
                              className="text-xs"
                              style={{ color: secondaryTextColor }}
                            >
                              {(images[index].size / 1024).toFixed(1)} KB
                            </div>
                            <button
                              type="button"
                              className="w-full rounded-md border px-2 py-1 text-xs font-semibold transition-colors"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)',
                                backgroundColor: theme === 'dark' ? 'rgba(190, 18, 60, 0.1)' : 'rgba(254, 242, 242, 0.9)',
                                color: theme === 'dark' ? '#fca5a5' : '#dc2626',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = theme === 'dark' ? '#f87171' : '#dc2626';
                                e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(190, 18, 60, 0.2)' : '#fee2e2';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)';
                                e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(190, 18, 60, 0.1)' : 'rgba(254, 242, 242, 0.9)';
                              }}
                              onClick={() => handleRemoveImage(index)}
                            >
                              ✕ Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Drop/Paste Zone */}
                <div
                  className="mt-3 cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-all duration-200"
                  style={{
                    borderColor: dragZoneBorder,
                    backgroundColor: dragZoneBg,
                  }}
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onDragLeave={(e) => e.preventDefault()}
                  onClick={() => document.getElementById('feedback-images')?.click()}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = dragZoneHoverBorder;
                    e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = dragZoneBorder;
                    e.currentTarget.style.backgroundColor = dragZoneBg;
                  }}
                >
                  <div className="mb-2 text-4xl">📋</div>
                  <p 
                    className="mb-1 text-sm font-medium"
                    style={{ color: labelColor }}
                  >
                    Click here or press Ctrl+V to paste images from clipboard
                  </p>
                  <p 
                    className="text-xs"
                    style={{ color: secondaryTextColor }}
                  >
                    You can paste multiple images at once
                  </p>
                </div>
              </div>

              {/* Form Actions */}
              <div className="flex flex-col gap-2 pt-2 sm:flex-row sm:justify-end">
                {onCancel && (
                  <button
                    type="button"
                    onClick={onCancel}
                    className="rounded-lg border px-4 py-2 text-sm font-semibold transition-all duration-200"
                    style={{
                      borderColor: cancelButtonBorder,
                      backgroundColor: cancelButtonBg,
                      color: cancelButtonText,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = cancelButtonHoverBorder;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = cancelButtonBorder;
                    }}
                  >
                    ← Cancel
                  </button>
                )}
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg border px-6 py-2 text-sm font-semibold text-white shadow-md transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50"
                  style={{
                    borderColor: submitButtonBg,
                    backgroundColor: submitButtonBg,
                  }}
                  onMouseEnter={(e) => {
                    if (!loading) {
                      e.currentTarget.style.backgroundColor = submitButtonHoverBg;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!loading) {
                      e.currentTarget.style.backgroundColor = submitButtonBg;
                    }
                  }}
                >
                  {loading ? (
                    <>
                      <span className="inline-block animate-spin">⏳</span> Submitting...
                    </>
                  ) : (
                    <>
                      📤 Submit Feedback
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

