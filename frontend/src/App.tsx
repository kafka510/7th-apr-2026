import KpiDashboard from './features/kpi/KpiDashboard';
import { TicketAdmin } from './features/ticketing/TicketAdmin';
import TicketCreate from './features/ticketing/TicketCreate';
import TicketDashboard from './features/ticketing/TicketDashboard';
import TicketEdit from './features/ticketing/TicketEdit';
import TicketDetailComponent from './features/ticketing/TicketDetail';
import TicketList from './features/ticketing/TicketList';
import YieldReport from './features/yield/YieldReport';
import { YieldDrilldown } from './features/yield/YieldDrilldown';
import { GenerationReport } from './features/generation/GenerationReport';
import { PortfolioMap } from './features/portfolio-map/PortfolioMap';
import { Sales } from './features/sales/Sales';
import { PrGap } from './features/pr-gap/PrGap';
import { RevenueLoss } from './features/revenue-loss/RevenueLoss';
import { AreasOfConcern } from './features/areas-of-concern/AreasOfConcern';
import { BessV1Dashboard } from './features/bess-v1-dashboard/BessV1Dashboard';
import { BESSPerformance } from './features/bess-performance/BESSPerformance';
import { MinamataTyphoonDamage } from './features/minamata-typhoon-damage/MinamataTyphoonDamage';
import { ICBudgetVsExpected } from './features/ic-budget/ICBudgetVsExpected';
import { Analytics } from './features/analytics/Analytics';
import { ApiManual } from './features/api/ApiManual';
import { DataUpload } from './features/data-upload/DataUpload';
import { DataUploadHelp } from './features/data-upload-help/DataUploadHelp';
import { SiteOnboarding } from './features/site-onboarding/SiteOnboarding';
import { SiteOnboardingWizard } from './features/site-onboarding/SiteOnboardingWizard';
import { UserManagement } from './features/user-management/UserManagement';
import { Feedback } from './features/feedback/Feedback';
import { UnifiedOperationsDashboard } from './features/unified-dashboard/UnifiedOperationsDashboard';
import { CalculationTest } from './features/calculation-test/CalculationTest';
import { EnergyRevenueHub } from './features/energy-revenue-hub/EnergyRevenueHub';
import { EngineeringTools } from './features/engineering-tools/EngineeringTools';
import { BackgroundJobs } from '@/features/background-jobs/BackgroundJobs';
import { ThemeProvider } from './contexts/ThemeContext';
import { ExportTaskProvider } from './contexts/ExportTaskContext';
import { Component, useEffect } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

type AppKey =
  | 'kpi-dashboard'
  | 'ticketing-dashboard'
  | 'ticketing-list'
  | 'ticketing-detail'
  | 'ticketing-create'
  | 'ticketing-edit'
  | 'ticketing-admin'
  | 'yield-report'
  | 'yield-drilldown'
  | 'generation-report'
  | 'portfolio-map'
  | 'sales'
  | 'pr-gap'
  | 'revenue-loss'
  | 'areas-of-concern'
  | 'bess-performance'
  | 'bess-v1-dashboard'
  | 'minamata-typhoon-damage'
  | 'ic-budget-vs-expected'
  | 'analytics'
  | 'api-manual'
  | 'data-upload'
  | 'data-upload-help'
  | 'site-onboarding'
  | 'site-onboarding-wizard'
  | 'user-management'
  | 'feedback-submit'
  | 'feedback-list'
  | 'unified-operations-dashboard'
  | 'calculation_test'
  | 'energy-revenue-hub'
  | 'engineering-tools'
  | 'background-jobs';

const resolveAppKey = (): AppKey => {
  if (typeof document === 'undefined') {
    return 'kpi-dashboard';
  }

  const root = document.getElementById('react-root');
  if (!root) {
    return 'kpi-dashboard';
  }

  const datasetKey = root.dataset.app;
  if (datasetKey === 'ticketing-dashboard' || root.classList.contains('js-react-ticket-dashboard')) {
    return 'ticketing-dashboard';
  }

  if (datasetKey === 'ticketing-list' || root.classList.contains('js-react-ticket-list')) {
    return 'ticketing-list';
  }

  if (datasetKey === 'ticketing-detail' || root.classList.contains('js-react-ticket-detail')) {
    return 'ticketing-detail';
  }

  if (datasetKey === 'ticketing-create' || root.classList.contains('js-react-ticket-create')) {
    return 'ticketing-create';
  }

  if (datasetKey === 'ticketing-edit' || root.classList.contains('js-react-ticket-edit')) {
    return 'ticketing-edit';
  }

  if (datasetKey === 'ticketing-admin' || root.classList.contains('js-react-ticket-admin')) {
    return 'ticketing-admin';
  }

  if (datasetKey === 'yield-report' || root.classList.contains('js-react-yield-report')) {
    return 'yield-report';
  }

  if (datasetKey === 'yield-drilldown' || root.classList.contains('js-react-yield-drilldown')) {
    return 'yield-drilldown';
  }

  if (datasetKey === 'generation-report' || root.classList.contains('js-react-generation-report')) {
    return 'generation-report';
  }

  if (datasetKey === 'portfolio-map' || root.classList.contains('js-react-portfolio-map')) {
    return 'portfolio-map';
  }

  if (datasetKey === 'sales' || root.classList.contains('js-react-sales')) {
    return 'sales';
  }

  if (datasetKey === 'pr-gap' || root.classList.contains('js-react-pr-gap')) {
    return 'pr-gap';
  }

  if (datasetKey === 'revenue-loss' || root.classList.contains('js-react-revenue-loss')) {
    return 'revenue-loss';
  }

  if (datasetKey === 'areas-of-concern' || root.classList.contains('js-react-areas-of-concern')) {
    return 'areas-of-concern';
  }

  if (datasetKey === 'bess-v1-dashboard' || root.classList.contains('js-react-bess-v1-dashboard')) {
    return 'bess-v1-dashboard';
  }

  if (datasetKey === 'bess-performance' || root.classList.contains('js-react-bess-performance')) {
    return 'bess-performance';
  }

  if (datasetKey === 'minamata-typhoon-damage' || root.classList.contains('js-react-minamata-typhoon-damage')) {
    return 'minamata-typhoon-damage';
  }

  if (datasetKey === 'ic-budget-vs-expected' || root.classList.contains('js-react-ic-budget-vs-expected')) {
    return 'ic-budget-vs-expected';
  }

  if (datasetKey === 'analytics' || root.classList.contains('js-react-analytics')) {
    return 'analytics';
  }
  
  if (datasetKey === 'calculation_test' || root.classList.contains('js-react-calculation-test')) {
    return 'calculation_test';
  }

  if (datasetKey === 'api-manual' || root.classList.contains('js-react-api-manual')) {
    return 'api-manual';
  }

  if (datasetKey === 'data-upload' || root.classList.contains('js-react-data-upload')) {
    return 'data-upload';
  }

  if (datasetKey === 'data-upload-help' || root.classList.contains('js-react-data-upload-help')) {
    return 'data-upload-help';
  }

  if (datasetKey === 'site-onboarding' || root.dataset.page === 'site-onboarding') {
    return 'site-onboarding';
  }

  if (datasetKey === 'site-onboarding-wizard' || root.classList.contains('js-react-site-onboarding-wizard')) {
    return 'site-onboarding-wizard';
  }

  if (datasetKey === 'user-management' || root.classList.contains('js-react-user-management')) {
    return 'user-management';
  }

  if (datasetKey === 'feedback-submit' || root.classList.contains('js-react-feedback-submit')) {
    return 'feedback-submit';
  }

  if (datasetKey === 'feedback-list' || root.classList.contains('js-react-feedback-list')) {
    return 'feedback-list';
  }

  if (datasetKey === 'unified-operations-dashboard' || root.classList.contains('js-react-unified-operations-dashboard')) {
    return 'unified-operations-dashboard';
  }

  if (datasetKey === 'energy-revenue-hub' || root.classList.contains('js-react-energy-revenue-hub')) {
    return 'energy-revenue-hub';
  }

  if (datasetKey === 'engineering-tools' || root.classList.contains('js-react-engineering-tools')) {
    return 'engineering-tools';
  }

  if (datasetKey === 'background-jobs' || root.classList.contains('js-react-background-jobs')) {
    return 'background-jobs';
  }

  return 'kpi-dashboard';
};

const App = () => {
  // For Playwright/SPA: Check if there's an initial route set in localStorage
  // This allows Playwright to navigate to the correct route before React loads
  useEffect(() => {
    const initialRoute = localStorage.getItem('spa-initial-route');
    if (initialRoute) {
      // Remove it immediately to prevent loops
      localStorage.removeItem('spa-initial-route');
      
      // Only navigate if we're not already on that route
      const currentPath = window.location.pathname + window.location.search;
      if (currentPath !== initialRoute) {
        window.location.href = initialRoute;
      }
    }
  }, []);

  const appKey = resolveAppKey();

  const content = () => {
    if (appKey === 'ticketing-dashboard') {
      return <TicketDashboard />;
    }

    if (appKey === 'ticketing-list') {
      return <TicketList />;
    }

    if (appKey === 'ticketing-detail') {
      const root = document.getElementById('react-root');
      const ticketId = root?.dataset.ticketId ?? null;
      return <TicketDetailComponent ticketId={ticketId} />;
    }

    if (appKey === 'ticketing-create') {
      return <TicketCreate />;
    }

    if (appKey === 'ticketing-edit') {
      return <TicketEdit />;
    }

    if (appKey === 'ticketing-admin') {
      const root = document.getElementById('react-root');
      const isSuperuser = root?.dataset.isSuperuser === 'true';
      return <TicketAdmin isSuperuser={isSuperuser} />;
    }

    if (appKey === 'yield-report') {
      return <YieldReport />;
    }

    if (appKey === 'yield-drilldown') {
      return <YieldDrilldown />;
    }

    if (appKey === 'generation-report') {
      return <GenerationReport />;
    }

    if (appKey === 'portfolio-map') {
      return <PortfolioMap />;
    }

    if (appKey === 'sales') {
      return <Sales />;
    }

    if (appKey === 'pr-gap') {
      return <PrGap />;
    }

    if (appKey === 'revenue-loss') {
      return <RevenueLoss />;
    }

    if (appKey === 'areas-of-concern') {
      return <AreasOfConcern />;
    }

    if (appKey === 'bess-v1-dashboard') {
      return <BessV1Dashboard />;
    }

    if (appKey === 'bess-performance') {
      return <BESSPerformance />;
    }

    if (appKey === 'minamata-typhoon-damage') {
      return <MinamataTyphoonDamage />;
    }

    if (appKey === 'ic-budget-vs-expected') {
      return <ICBudgetVsExpected />;
    }

    if (appKey === 'analytics') {
      return <Analytics />;
    }
    
    if (appKey === 'calculation_test') {
      return <CalculationTest />;
    }

    if (appKey === 'api-manual') {
      return <ApiManual />;
    }

    if (appKey === 'data-upload') {
      return <DataUpload />;
    }

    if (appKey === 'data-upload-help') {
      return <DataUploadHelp />;
    }

    if (appKey === 'site-onboarding') {
      return <SiteOnboarding />;
    }

    if (appKey === 'site-onboarding-wizard') {
      return <SiteOnboardingWizard />;
    }

    if (appKey === 'user-management') {
      return <UserManagement />;
    }

    if (appKey === 'feedback-submit') {
      return <Feedback mode="submit" />;
    }

    if (appKey === 'feedback-list') {
      const root = document.getElementById('react-root');
      const isSuperuser = root?.dataset.isSuperuser === 'true';
      return <Feedback mode="list" isSuperuser={isSuperuser} />;
    }

    if (appKey === 'unified-operations-dashboard') {
      return <UnifiedOperationsDashboard />;
    }

    if (appKey === 'energy-revenue-hub') {
      return <EnergyRevenueHub />;
    }

    if (appKey === 'engineering-tools') {
      return <EngineeringTools />;
    }

    if (appKey === 'background-jobs') {
      const root = document.getElementById('react-root');
      const isSuperuser = root?.dataset.isSuperuser === 'true';
      return <BackgroundJobs isSuperuser={isSuperuser} />;
    }

    return <KpiDashboard />;
  };

  return (
    <ThemeProvider>
      <ExportTaskProvider>
        <AppBoundary appKey={appKey}>{content()}</AppBoundary>
      </ExportTaskProvider>
    </ThemeProvider>
  );
};

export default App;

class AppBoundary extends Component<{ children: ReactNode; appKey: AppKey }, { hasError: boolean; message: string }> {
  constructor(props: { children: ReactNode; appKey: AppKey }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): { hasError: boolean; message: string } {
    return { hasError: true, message: error?.message || 'Unknown React error' };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const msg = String(error?.message ?? '');
    const hint = /useEffect|useState|Cannot read properties of null/i.test(msg)
      ? 'Possible duplicate `react` in split chunks or a blocked JS chunk (check Network for failed .js files).'
      : undefined;
    console.error('[AppBoundary] render crash', {
      appKey: this.props.appKey,
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      path: window.location.pathname,
      hint,
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '16px', margin: '12px', border: '1px solid #fecaca', background: '#fef2f2', color: '#991b1b' }}>
          <strong>UI crashed while rendering this page.</strong>
          <div style={{ marginTop: '8px', fontSize: '12px' }}>
            app: {this.props.appKey} | error: {this.state.message}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
