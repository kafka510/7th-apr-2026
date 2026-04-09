import { useTheme } from '../../contexts/ThemeContext';
import { TicketCategoriesAdmin } from './components/TicketCategoriesAdmin';
import { TicketSubCategoriesAdmin } from './components/TicketSubCategoriesAdmin';
import { LossCategoriesAdmin } from './components/LossCategoriesAdmin';
import { PMRulesAdmin } from './components/PMRulesAdmin';

type TicketAdminProps = {
  isSuperuser: boolean;
};

export const TicketAdmin = ({ isSuperuser }: TicketAdminProps) => {
  const { theme } = useTheme();
  
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  
  return (
    <div 
      className="mx-auto min-h-screen max-w-7xl px-4 py-8"
      style={{
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
      }}
    >
      <header className="mb-8">
        <div>
          <h1 
            className="text-3xl font-bold"
            style={{ color: textColor }}
          >
            Ticketing Admin
          </h1>
          <p 
            className="mt-2 text-sm"
            style={{ color: secondaryTextColor }}
          >
            Manage ticket categories, sub-categories, loss categories, and PM rules
          </p>
        </div>
      </header>

      <div className="space-y-6">
        <TicketCategoriesAdmin isSuperuser={isSuperuser} />
        <TicketSubCategoriesAdmin isSuperuser={isSuperuser} />
        <LossCategoriesAdmin isSuperuser={isSuperuser} />
        <PMRulesAdmin isSuperuser={isSuperuser} />
      </div>
    </div>
  );
};

