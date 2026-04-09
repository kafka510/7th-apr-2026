import { useState, useMemo } from 'react';
import { MapPanel } from './LocationMap';
import { StepperHeader } from './StepperHeader';
import { StepPanel, getStepComplete } from './StepPanel';
import type { SolarGISMonthlyResponse } from './StepPanel';
import { WizardNavigation } from './WizardNavigation';

interface SiteSetupWizardProps {
  location: { lat: number; lng: number } | null;
  onLocationSelect: (lat: number, lng: number) => void;
  csvFile: File | null;
  onCsvFileSelect: (file: File | null) => void;
  kmlFile: File | null;
  onKmlFileSelect: (file: File | null) => void;
  isParsingSolargis: boolean;
  solargisError: string | null;
  solargisPreview: SolarGISMonthlyResponse | null;
}

export default function SiteSetupWizard({
  location,
  onLocationSelect,
  csvFile,
  onCsvFileSelect,
  kmlFile,
  onKmlFileSelect,
  isParsingSolargis,
  solargisError,
  solargisPreview,
}: SiteSetupWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);

  const stepComplete = useMemo(
    () => getStepComplete(location, solargisPreview, kmlFile),
    [location, solargisPreview, kmlFile]
  );

  const isCurrentStepComplete =
    currentStep === 1
      ? stepComplete.location
      : currentStep === 2
        ? stepComplete.climate
        : currentStep === 3
          ? stepComplete.boundary
          : true;

  const isLastStep = currentStep === 4;

  const handleNext = () => {
    if (currentStep < 4) setCurrentStep((s) => s + 1);
  };

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep((s) => s - 1);
  };

  const showMap = currentStep === 1;

  return (
    <div className="max-w-[1440px] mx-auto p-3 flex flex-col gap-3">
      <StepperHeader currentStep={currentStep} completedSteps={stepComplete} />

      <div
        className={
          showMap
            ? 'grid min-h-[320px] gap-3'
            : 'min-h-[280px]'
        }
        style={
          showMap
            ? { gridTemplateColumns: '2fr 1fr', gap: '12px' }
            : undefined
        }
      >
        {showMap && (
          <div
            className="rounded-lg overflow-hidden bg-white shadow-sm sticky top-0"
            style={{ borderRadius: '8px', minHeight: '320px', alignSelf: 'stretch' }}
          >
            <MapPanel
              location={location}
              onLocationSelect={onLocationSelect}
              className="min-h-[320px] h-full w-full"
            />
          </div>
        )}

        <div
          className={
            showMap
              ? 'rounded-lg bg-white p-4 shadow-sm flex flex-col gap-3 overflow-hidden'
              : 'rounded-lg bg-white p-4 shadow-sm flex flex-col gap-3 overflow-auto'
          }
          style={{ borderRadius: '8px' }}
        >
          <StepPanel
            currentStep={currentStep}
            location={location}
            onLocationSelect={onLocationSelect}
            csvFile={csvFile}
            onCsvFileSelect={onCsvFileSelect}
            isParsingSolargis={isParsingSolargis}
            solargisError={solargisError}
            solargisPreview={solargisPreview}
            kmlFile={kmlFile}
            onKmlFileSelect={onKmlFileSelect}
          />
        </div>
      </div>

      <WizardNavigation
        currentStep={currentStep}
        stepComplete={isCurrentStepComplete}
        onBack={handleBack}
        onNext={handleNext}
        isLastStep={isLastStep}
      />
    </div>
  );
}
