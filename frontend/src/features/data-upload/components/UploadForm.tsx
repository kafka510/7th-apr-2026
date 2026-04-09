/**
 * Upload Form Component - React Style V1
 */
 
import { useState } from 'react';
import type { FormEvent, ChangeEvent } from 'react';
import type { DataType, UploadMode } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface UploadFormProps {
  onUpload: (
    file: File,
    dataType: DataType,
    uploadMode: UploadMode,
    options?: {
      startDate?: string;
      endDate?: string;
      skipDuplicates?: boolean;
      validateData?: boolean;
      batchSize?: number;
    }
  ) => Promise<void>;
  isUploading: boolean;
}

export function UploadForm({ onUpload, isUploading }: UploadFormProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(8, 12, 7);
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  
  const [dataType, setDataType] = useState<DataType | ''>('');
  const [uploadMode, setUploadMode] = useState<UploadMode>('append');
  const [file, setFile] = useState<File | null>(null);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [validateData, setValidateData] = useState(true);
  const [batchSize, setBatchSize] = useState(1000);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Theme-aware colors
  const cardBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textSecondary = theme === 'dark' ? '#94a3b8' : '#64748b';
  const textTertiary = theme === 'dark' ? '#64748b' : '#94a3b8';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.9)';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const inputHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const inputFocusBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const inputFocusRing = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.2)';
  const radioBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.9)';
  const radioBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const radioColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const checkboxBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.9)';
  const checkboxBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const checkboxColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const submitButtonBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const submitButtonBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const submitButtonText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const submitButtonHoverBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.4)' : 'rgba(59, 130, 246, 0.2)';
  const fileButtonBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const fileButtonText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const advancedBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : 'rgba(248, 250, 252, 0.8)';
  const advancedBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!file || !dataType) {
      return;
    }

    const options: {
      startDate?: string;
      endDate?: string;
      skipDuplicates?: boolean;
      validateData?: boolean;
      batchSize?: number;
    } = {
      skipDuplicates,
      validateData,
      batchSize,
    };

    // Use explicit date range for replace mode
    if (uploadMode === 'replace') {
      if (startDate) {
        options.startDate = startDate;
      }
      if (endDate) {
        options.endDate = endDate;
      }
    }

    await onUpload(file, dataType, uploadMode, options);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <div 
      className="flex h-full flex-col rounded-xl border p-3 shadow-xl"
      style={{
        borderColor: cardBorder,
        background: cardBg,
      }}
    >
      <h5 className="mb-3 text-sm font-bold" style={{ color: textPrimary }}>📁 Upload Data Files</h5>

      <form onSubmit={handleSubmit} id="uploadForm" className="flex flex-col gap-3">
        {/* Data Type Selection */}
        <div className="space-y-1">
          <label htmlFor="data_type" className="font-semibold uppercase tracking-wide" style={{ color: textSecondary, fontSize: `${labelFontSize}px` }}>
            <span style={{ fontSize: `${bodyFontSize}px` }}>📋</span> Data Type
          </label>
          <select
            className="w-full rounded-lg border px-2 py-1 font-medium shadow-inner transition"
            style={{
              fontSize: `${bodyFontSize}px`,
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            id="data_type"
            value={dataType}
            onChange={(e) => setDataType(e.target.value as DataType)}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = inputHoverBorder;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = inputBorder;
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = inputFocusBorder;
              e.currentTarget.style.outline = 'none';
              e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusRing}`;
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = inputBorder;
              e.currentTarget.style.boxShadow = 'none';
            }}
            required
          >
            <option value="">Select Data Type</option>
            <option value="yield">Yield Data</option>
            <option value="bess">BESS Data</option>
            <option value="bess_v1">BESS V1 Data</option>
            <option value="aoc">Areas of Concern (AOC)</option>
            <option value="ice">ICE Data</option>
            <option value="icvsexvscur">IC Budget vs Expected Data</option>
            <option value="map">Map Data</option>
            <option value="minamata">Minamata String Loss</option>
            <option value="loss_calculation">Loss Calculation</option>
            <option value="actual_generation_daily">Actual Generation Daily</option>
            <option value="expected_budget_daily">Expected Budget Daily</option>
            <option value="budget_gii_daily">Budget GII Daily</option>
            <option value="actual_gii_daily">Actual GII Daily</option>
            <option value="ic_approved_budget_daily">IC Approved Budget Daily</option>
          </select>
        </div>

        {/* Upload Mode */}
        <div className="space-y-1">
          <label className="font-semibold uppercase tracking-wide" style={{ color: textSecondary, fontSize: `${labelFontSize}px` }}>
            <span style={{ fontSize: `${bodyFontSize}px` }}>⚙️</span> Upload Mode
          </label>
          <div className="space-y-2">
            <label 
              className="flex cursor-pointer items-center gap-2 rounded-lg border px-2 py-1.5 transition"
              style={{
                borderColor: radioBorder,
                backgroundColor: radioBg,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = inputHoverBorder;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = radioBorder;
              }}
            >
              <input
                type="radio"
                name="upload_mode"
                value="append"
                checked={uploadMode === 'append'}
                onChange={(e) => setUploadMode(e.target.value as UploadMode)}
                className="size-3"
                style={{
                  accentColor: radioColor,
                }}
              />
              <span className="font-medium" style={{ color: inputText, fontSize: `${bodyFontSize}px` }}>📈 Append New Data</span>
            </label>
            <label 
              className="flex cursor-pointer items-center gap-2 rounded-lg border px-2 py-1.5 transition"
              style={{
                borderColor: radioBorder,
                backgroundColor: radioBg,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = inputHoverBorder;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = radioBorder;
              }}
            >
              <input
                type="radio"
                name="upload_mode"
                value="replace"
                checked={uploadMode === 'replace'}
                onChange={(e) => setUploadMode(e.target.value as UploadMode)}
                className="size-3"
                style={{
                  accentColor: radioColor,
                }}
              />
              <span className="font-medium" style={{ color: inputText, fontSize: `${bodyFontSize}px` }}>🔄 Replace/Update Existing Data</span>
            </label>
          </div>
        </div>

        {/* Date Range for Replace Mode */}
        {uploadMode === 'replace' && (
          <div className="space-y-1">
            <label className="text-[8px] font-semibold uppercase tracking-wide" style={{ color: textSecondary }}>
              <span className="text-[10px]">📅</span> Date Range for Update
            </label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div className="space-y-1">
                <span className="text-[9px] font-medium" style={{ color: textSecondary }}>Start Date</span>
                <input
                  type="date"
                  className="w-full rounded-lg border px-2 py-1 text-[10px] font-medium transition"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  placeholder="mm/dd/yyyy"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = inputHoverBorder;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.outline = 'none';
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusRing}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
              </div>
              <div className="space-y-1">
                <span className="text-[9px] font-medium" style={{ color: textSecondary }}>End Date</span>
                <input
                  type="date"
                  className="w-full rounded-lg border px-2 py-1 text-[10px] font-medium transition"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  placeholder="mm/dd/yyyy"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = inputHoverBorder;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.outline = 'none';
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusRing}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
              </div>
            </div>
            <p className="text-[9px]" style={{ color: textTertiary }}>Choose the exact start and end dates to update existing data.</p>
          </div>
        )}

        {/* File Upload */}
        <div className="space-y-1">
          <label htmlFor="csv_file" className="text-[8px] font-semibold uppercase tracking-wide" style={{ color: textSecondary }}>
            <span className="text-[10px]">📄</span> CSV File
          </label>
          <input
            type="file"
            className="w-full cursor-pointer rounded-lg border px-2 py-1 text-[10px] font-medium transition file:mr-2 file:cursor-pointer file:rounded file:border-0 file:px-2 file:py-0.5 file:text-[9px] file:font-semibold"
            style={{
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            id="csv_file"
            accept=".csv"
            onChange={handleFileChange}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = inputHoverBorder;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = inputBorder;
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = inputFocusBorder;
              e.currentTarget.style.outline = 'none';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = inputBorder;
            }}
            required
          />
          <style>{`
            input[type="file"]::file-selector-button {
              background-color: ${fileButtonBg};
              color: ${fileButtonText};
            }
          `}</style>
          <p className="text-[9px]" style={{ color: textTertiary }}>Upload CSV file with appropriate headers</p>
        </div>

        {/* Advanced Options */}
        <div className="space-y-2">
          <button
            className="rounded-lg border px-3 py-1.5 text-[10px] font-semibold transition"
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = buttonHoverBorder;
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = buttonBorder;
              e.currentTarget.style.backgroundColor = buttonBg;
            }}
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            ⚙️ Advanced Options {showAdvanced ? '▲' : '▼'}
          </button>
          {showAdvanced && (
            <div 
              className="space-y-2 rounded-lg border p-3"
              style={{
                borderColor: advancedBorder,
                backgroundColor: advancedBg,
              }}
            >
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  id="skip_duplicates"
                  checked={skipDuplicates}
                  onChange={(e) => setSkipDuplicates(e.target.checked)}
                  className="size-3.5 rounded"
                  style={{
                    borderColor: checkboxBorder,
                    backgroundColor: checkboxBg,
                    accentColor: checkboxColor,
                  }}
                />
                <span className="text-[10px] font-medium" style={{ color: inputText }}>Skip duplicate records</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  id="validate_data"
                  checked={validateData}
                  onChange={(e) => setValidateData(e.target.checked)}
                  className="size-3.5 rounded"
                  style={{
                    borderColor: checkboxBorder,
                    backgroundColor: checkboxBg,
                    accentColor: checkboxColor,
                  }}
                />
                <span className="text-[10px] font-medium" style={{ color: inputText }}>Validate data before import</span>
              </label>
              <div className="space-y-1">
                <label htmlFor="batch_size" className="text-[9px] font-semibold" style={{ color: textSecondary }}>
                  Batch Size
                </label>
                <input
                  type="number"
                  className="w-full rounded-lg border px-2 py-1 text-[10px] font-medium transition"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  id="batch_size"
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number.parseInt(e.target.value, 10))}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = inputHoverBorder;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.outline = 'none';
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusRing}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                  min={100}
                  max={10000}
                />
              </div>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="rounded-lg border px-4 py-2 text-xs font-semibold transition hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            borderColor: submitButtonBorder,
            backgroundColor: submitButtonBg,
            color: submitButtonText,
          }}
          onMouseEnter={(e) => {
            if (!e.currentTarget.disabled) {
              e.currentTarget.style.backgroundColor = submitButtonHoverBg;
            }
          }}
          onMouseLeave={(e) => {
            if (!e.currentTarget.disabled) {
              e.currentTarget.style.backgroundColor = submitButtonBg;
            }
          }}
          disabled={
            isUploading ||
            !file ||
            !dataType ||
            (uploadMode === 'replace' && (!startDate || !endDate))
          }
        >
          {isUploading ? (
            <>
              <span 
                className="mr-2 inline-block size-3 animate-spin rounded-full border-2 border-t-transparent"
                style={{
                  borderColor: submitButtonText,
                }}
              ></span>
              Uploading...
            </>
          ) : (
            '📤 Upload Data'
          )}
        </button>
      </form>
    </div>
  );
}

