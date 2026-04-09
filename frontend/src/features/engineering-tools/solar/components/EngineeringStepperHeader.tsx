import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const STEPS = [
  { id: 1, label: 'Loss Factors' },
  { id: 2, label: 'Site Orientation' },
  { id: 3, label: 'Module Assumptions' },
  { id: 4, label: 'String Config' },
  { id: 5, label: 'System Config' },
] as const;

export interface EngineeringStepCompleteState {
  step1: boolean;
  step2: boolean;
  step3: boolean;
  step4: boolean;
  step5: boolean;
}

interface EngineeringStepperHeaderProps {
  currentStep: number;
  completedSteps: EngineeringStepCompleteState;
}

export function EngineeringStepperHeader({ currentStep, completedSteps }: EngineeringStepperHeaderProps) {
  const isStepComplete = (step: number): boolean => {
    if (step === 1) return completedSteps.step1;
    if (step === 2) return completedSteps.step2;
    if (step === 3) return completedSteps.step3;
    if (step === 4) return completedSteps.step4;
    if (step === 5) return completedSteps.step5;
    return false;
  };

  return (
    <header className="h-9 px-2 py-1.5 border-b border-gray-200 flex items-center">
      <nav className="flex items-center gap-1.5 w-full" aria-label="Engineering setup progress">
        {STEPS.map((step, index) => {
          const completed = isStepComplete(step.id);
          const active = currentStep === step.id;
          const isLast = index === STEPS.length - 1;

          return (
            <div key={step.id} className="flex items-center flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div
                  className={cn(
                    'flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border-2 text-xs font-medium transition-colors',
                    completed && 'border-green-600 bg-green-600 text-white',
                    active && !completed && 'border-blue-600 bg-blue-600 text-white',
                    !active && !completed && 'border-gray-200 bg-white text-gray-600'
                  )}
                  aria-current={active ? 'step' : undefined}
                >
                  {completed ? <Check className="h-3 w-3" /> : step.id}
                </div>
                <span
                  className={cn(
                    'text-sm font-medium hidden sm:inline',
                    active && 'text-blue-600',
                    completed && 'text-green-600',
                    !active && !completed && 'text-foreground'
                  )}
                >
                  {step.label}
                </span>
              </div>
              {!isLast && (
                <div
                  className={cn(
                    'mx-1 h-0.5 flex-1 min-w-[16px] max-w-[40px] rounded',
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
