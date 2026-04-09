import { useCallback, useState } from 'react';
import { Upload, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  title: string;
  description: string;
  acceptedType: '.csv' | '.kml';
  file: File | null;
  onFileSelect: (file: File | null) => void;
  icon: React.ReactNode;
  maxSizeMb?: number;
  /** Use in wizard steps for tighter spacing */
  compact?: boolean;
}

const FileUpload = ({
  title,
  description,
  acceptedType,
  file,
  onFileSelect,
  icon,
  maxSizeMb,
  compact,
}: FileUploadProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (selectedFile: File): boolean => {
    const extension = '.' + selectedFile.name.split('.').pop()?.toLowerCase();
    if (extension !== acceptedType) {
      setError(`Invalid file type. Please upload a ${acceptedType} file.`);
      return false;
    }
    if (maxSizeMb && selectedFile.size > maxSizeMb * 1024 * 1024) {
      setError(`File is too large. Maximum size is ${maxSizeMb} MB.`);
      return false;
    }
    setError(null);
    return true;
  };

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile && validateFile(droppedFile)) {
        onFileSelect(droppedFile);
      }
    },
    [acceptedType, onFileSelect]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      onFileSelect(selectedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const removeFile = () => {
    onFileSelect(null);
    setError(null);
  };

  return (
    <div className={cn('input-section-card overflow-hidden h-full', compact && 'rounded-lg')}>
      <div className={cn('border-b border-border bg-gradient-to-r from-primary/5 to-accent/5', compact ? 'p-2' : 'p-4')}>
        <div className="flex items-center gap-2">
          {icon}
          <h3 className={cn('font-semibold text-foreground', compact ? 'text-sm' : 'text-lg')}>{title}</h3>
        </div>
        <p className={cn('text-muted-foreground', compact ? 'text-xs mt-0.5' : 'text-sm mt-1')}>{description}</p>
      </div>
      <div className={compact ? 'p-2' : 'p-4'}>
        {!file ? (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={cn(
              'border-2 border-dashed transition-all duration-200 cursor-pointer',
              'hover:border-primary hover:bg-primary/10 hover:shadow-md',
              isDragging ? 'border-primary bg-primary/15 shadow-inner' : 'border-border bg-gradient-to-b from-muted/30 to-muted/10',
              compact ? 'rounded-lg p-4' : 'rounded-xl p-8'
            )}
          >
            <label className={cn('flex flex-col items-center cursor-pointer', compact ? 'gap-2' : 'gap-3')}>
              <div className={cn('rounded-full transition-all duration-200', isDragging ? 'bg-primary/30 scale-110' : 'bg-primary/10', compact ? 'p-2' : 'p-3')}>
                <Upload className={cn('text-primary transition-colors', compact ? 'w-5 h-5' : 'w-6 h-6')} />
              </div>
              <div className="text-center">
                <p className={cn('font-medium text-foreground', compact ? 'text-xs' : 'text-sm')}>Drop your file here or click to browse</p>
                <p className={cn('text-muted-foreground', compact ? 'text-xs mt-0.5' : 'text-xs mt-1')}>
                  Only {acceptedType} files accepted{maxSizeMb ? `, up to ${maxSizeMb} MB` : ''}
                </p>
              </div>
              <input type="file" accept={acceptedType} onChange={handleFileChange} className="hidden" />
            </label>
          </div>
        ) : (
          <div className={cn('flex items-center gap-3 bg-success/10 border border-success/20 rounded-lg', compact ? 'p-2' : 'p-4')}>
            <div className={cn('bg-success/20 rounded-lg', compact ? 'p-1.5' : 'p-2')}>
              <CheckCircle className={cn('text-success', compact ? 'w-4 h-4' : 'w-5 h-5')} />
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn('font-medium text-foreground truncate', compact ? 'text-xs' : 'text-sm')}>{file.name}</p>
              <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
            <button onClick={removeFile} className={cn('font-medium text-destructive hover:underline', compact ? 'text-xs' : 'text-sm')}>
              Remove
            </button>
          </div>
        )}
        {error && (
          <div className={cn('flex items-center gap-2 bg-destructive/10 border border-destructive/20 rounded-lg', compact ? 'mt-2 p-2' : 'mt-3 p-3')}>
            <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0" />
            <p className={cn('text-destructive', compact ? 'text-xs' : 'text-sm')}>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
