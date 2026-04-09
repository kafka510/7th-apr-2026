import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface WizardNavigationProps {
  currentStep: number;
  stepComplete: boolean;
  onBack: () => void;
  onNext: () => void;
  isLastStep: boolean;
}

export function WizardNavigation({
  currentStep,
  stepComplete,
  onBack,
  onNext,
  isLastStep,
}: WizardNavigationProps) {
  const showBack = currentStep > 1;

  return (
    <div className="h-8 flex items-center justify-end gap-2">
      {showBack && (
        <Button type="button" variant="outline" size="sm" onClick={onBack} className="gap-1.5 h-8">
          <ChevronLeft className="w-3.5 h-3.5" />
          Back
        </Button>
      )}
      {!isLastStep && (
        <Button
          type="button"
          size="sm"
          onClick={onNext}
          disabled={!stepComplete}
          className="gap-1.5 h-8 bg-blue-600 hover:bg-blue-700 text-white"
        >
          Next
          <ChevronRight className="w-3.5 h-3.5" />
        </Button>
      )}
    </div>
  );
}
