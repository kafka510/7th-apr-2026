import { useState, useMemo } from 'react';
import { EngineeringStepperHeader } from './EngineeringStepperHeader';
import type { EngineeringStepCompleteState } from './EngineeringStepperHeader';
import { WizardNavigation } from './WizardNavigation';
import LossFactorsBlock from './LossFactorsBlock';
import SiteOrientationBlock from './SiteOrientationBlock';
import ModuleAssumptionsBlock from './ModuleAssumptionsBlock';
import StringConfigurationBlock from './StringConfigurationBlock';
import SystemConfigurationBlock from './SystemConfigurationBlock';
import type { SystemConfigLayoutParams } from './SystemConfigurationBlock';

interface EngineeringWizardProps {
  location: { lat: number; lng: number } | null;
  onLossFactorsChange: (p: { dcLossPct: number; acLossPct: number; shadowLossPct: number }) => void;
  onInverterRatedPowerChange: (kw: number | null) => void;
  onLayoutParamsChange: (params: SystemConfigLayoutParams) => void;
}

export default function EngineeringWizard({
  location,
  onLossFactorsChange,
  onInverterRatedPowerChange,
  onLayoutParamsChange,
}: EngineeringWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 5;
  const isLastStep = currentStep === totalSteps;

  const completedSteps: EngineeringStepCompleteState = useMemo(
    () => ({
      step1: currentStep > 1,
      step2: currentStep > 2,
      step3: currentStep > 3,
      step4: currentStep > 4,
      step5: currentStep > 5,
    }),
    [currentStep]
  );

  const handleNext = () => {
    if (currentStep < totalSteps) setCurrentStep((s) => s + 1);
  };

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep((s) => s - 1);
  };

  return (
    <div className="max-w-[1440px] mx-auto p-2 flex flex-col gap-2">
      <EngineeringStepperHeader currentStep={currentStep} completedSteps={completedSteps} />

      <div className="min-h-[200px] rounded-lg bg-white p-3 shadow-sm flex flex-col overflow-auto">
        {currentStep === 1 && (
          <LossFactorsBlock
            disabled={!location}
            onLossFactorsChange={onLossFactorsChange}
            defaultExpanded
          />
        )}
        {currentStep === 2 && <SiteOrientationBlock location={location} defaultExpanded />}
        {currentStep === 3 && <ModuleAssumptionsBlock location={location} defaultExpanded />}
        {currentStep === 4 && (
          <StringConfigurationBlock
            location={location}
            onInverterRatedPowerChange={onInverterRatedPowerChange}
            defaultExpanded
          />
        )}
        {currentStep === 5 && (
          <SystemConfigurationBlock
            location={location}
            onLayoutParamsChange={onLayoutParamsChange}
            defaultExpanded
          />
        )}
      </div>

      <WizardNavigation
        currentStep={currentStep}
        stepComplete={true}
        onBack={handleBack}
        onNext={handleNext}
        isLastStep={isLastStep}
      />
    </div>
  );
}
