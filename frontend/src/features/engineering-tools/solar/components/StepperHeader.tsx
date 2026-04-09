import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const STEPS = [
  { id: 1, label: 'Location' },
  { id: 2, label: 'Climate Data' },
  { id: 3, label: 'Site Boundary' },
  { id: 4, label: 'Review' },
] as const;

export interface StepCompleteState {
  location: boolean;
  climate: boolean;
  boundary: boolean;
}

interface StepperHeaderProps {
  currentStep: number;
  completedSteps: StepCompleteState;
}

export function StepperHeader({ currentStep, completedSteps }: StepperHeaderProps) {
  const isStepComplete = (step: number): boolean => {
    if (step === 1) return completedSteps.location;
    if (step === 2) return completedSteps.climate;
    if (step === 3) return completedSteps.boundary;
    if (step === 4) return completedSteps.location && completedSteps.climate && completedSteps.boundary;
    return false;
  };

  const isStepAccessible = (step: number): boolean => {
    if (step === 1) return true;
    if (step === 2) return completedSteps.location;
    if (step === 3) return completedSteps.location && completedSteps.climate;
    if (step === 4) return completedSteps.location && completedSteps.climate && completedSteps.boundary;
    return false;
  };

  return (
    <header className="h-12 px-3 py-2 border-b border-gray-200 flex items-center">
      <nav className="flex items-center gap-1.5 w-full" aria-label="Site setup progress">
        {STEPS.map((step, index) => {
          const completed = isStepComplete(step.id);
          const active = currentStep === step.id;
          const disabled = !isStepAccessible(step.id);
          const isLast = index === STEPS.length - 1;

          return (
            <div key={step.id} className="flex items-center flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div
                  className={cn(
                    'flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border-2 text-xs font-medium transition-colors',
                    completed && 'border-green-600 bg-green-600 text-white',
                    active && !completed && 'border-blue-600 bg-blue-600 text-white',
                    disabled && !active && !completed && 'border-gray-200 bg-gray-50 text-gray-400',
                    !disabled && !active && !completed && 'border-gray-200 bg-white text-gray-600'
                  )}
                  aria-current={active ? 'step' : undefined}
                >
                  {completed ? <Check className="h-3.5 w-3.5" /> : step.id}
                </div>
                <span
                  className={cn(
                    'text-sm font-medium hidden sm:inline',
                    active && 'text-blue-600',
                    completed && 'text-green-600',
                    disabled && 'text-gray-400',
                    !active && !completed && !disabled && 'text-foreground'
                  )}
                >
                  {step.label}
                </span>
              </div>
              {!isLast && (
                <div
                  className={cn(
                    'mx-1 h-0.5 flex-1 min-w-[16px] max-w-[60px] rounded',
                    completed ? 'bg-green-600' : 'bg-gray-200'
                  )}
                  aria-hidden
                />
              )}
            </div>
          );
        })}
      </nav>
    </header>
  );
}
