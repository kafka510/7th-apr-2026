/**
 * Generation Budget Insights - Summary Table Component
 * Portfolio-level summary for IC Budget vs Expected Generation
 */
import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { ICBudgetDataEntry, PortfolioSummary } from '../types';
import { parseNumeric } from '../utils/dataUtils';

interface SummaryTableProps {
  data: ICBudgetDataEntry[];
}

// Portfolio reasons mapping
const portfolioReasons: Record<string, string> = {
  'Korea-Blackwood': 'Backup data for IC approved budget is not available to find actual reasons for the difference.',
  'Korea-Iceberg': 'Backup data for IC approved budget is not available to find actual reasons for the difference.',
  'Singapore': 'NIL',
  'SG Matco Asia': 'NIL',
  'TW-Yunlin': 'NIL',
  'JP Minamata': 'Updated : Degradation Loss, IAM factor,Albedo.',
  'Korea-Sroof': 'Updated : Tilt Angle as per as built diagram.',
};

export function SummaryTable({ data }: SummaryTableProps) {
  const { theme } = useTheme();
  
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)';
  const tableHeaderBg = theme === 'dark'
    ? 'linear-gradient(to right, rgba(30, 41, 59, 0.8), rgba(51, 65, 85, 0.7))'
    : 'linear-gradient(to right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))';
  const tableHeaderText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const tableRowBg1 = theme === 'dark' ? 'rgba(15, 23, 42, 0.4)' : 'rgba(255, 255, 255, 0.8)';
  const tableRowBg2 = theme === 'dark' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(248, 250, 252, 0.8)';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowTextSecondary = theme === 'dark' ? '#cbd5e1' : '#475569';
  const noteBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.8), rgba(51, 65, 85, 0.7))'
    : 'linear-gradient(to bottom right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))';
  const noteBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)';
  const noteText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const noteTitleText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const noteTextSecondary = theme === 'dark' ? '#cbd5e1' : '#475569';
  const linkColor = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const linkHoverColor = theme === 'dark' ? '#93c5fd' : '#0056a3';
  
  const portfolioSummary = useMemo(() => {
    const summary: Record<string, PortfolioSummary> = {};

    data.forEach((row) => {
      const portfolio = row.portfolio || 'Unknown';
      if (!summary[portfolio]) {
        summary[portfolio] = {
          portfolio,
          icApprovedBudget: 0,
          expectedBudget: 0,
          actualGeneration: 0,
          difference: 0,
          reason: portfolioReasons[portfolio] || 'Backup data for IC approved budget is not available to find actual reasons for the difference.',
        };
      }

      summary[portfolio].icApprovedBudget += parseNumeric(row.ic_approved_budget_mwh);
      summary[portfolio].expectedBudget += parseNumeric(row.expected_budget_mwh);
      summary[portfolio].actualGeneration += parseNumeric(row.actual_generation_mwh);
    });

    // Calculate difference percentage
    Object.values(summary).forEach((item) => {
      if (item.expectedBudget > 0) {
        item.difference = ((item.icApprovedBudget - item.expectedBudget) / item.expectedBudget) * 100;
      }
    });

    return Object.values(summary).sort((a, b) => a.portfolio.localeCompare(b.portfolio));
  }, [data]);

  const formatNumber = (value: number): string => {
    if (!Number.isFinite(value)) {
      return '';
    }
    return Math.round(value).toLocaleString('en-IN');
  };

  const formatPercentage = (value: number): string => {
    if (!Number.isFinite(value)) {
      return '';
    }
    return value.toFixed(2) + '%';
  };

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse border text-[18px]" style={{ borderColor: tableBorder }}>
          <thead className="sticky top-0 z-10">
            <tr style={{ background: tableHeaderBg }}>
              <th 
                className="whitespace-nowrap border px-1 py-3 text-left text-[18px] font-semibold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                Portfolio
              </th>
              <th 
                className="whitespace-nowrap border px-1 py-3 text-left text-[18px] font-semibold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                IC Approved Budget (MWh)
              </th>
              <th 
                className="whitespace-nowrap border px-1 py-3 text-left text-[18px] font-semibold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                Expected Budget (MWh)
              </th>
              <th 
                className="whitespace-nowrap border px-1 py-3 text-left text-[18px] font-semibold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                Difference (%)
              </th>
              <th 
                className="border px-1 py-3 text-left text-[18px] font-semibold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                Reasons
              </th>
            </tr>
          </thead>
          <tbody>
            {portfolioSummary.map((item, idx) => (
              <tr 
                key={item.portfolio}
                style={{
                  backgroundColor: idx % 2 === 0 ? tableRowBg1 : tableRowBg2,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = tableRowHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = idx % 2 === 0 ? tableRowBg1 : tableRowBg2;
                }}
              >
                <td 
                  className="whitespace-nowrap border px-1 py-2 text-[18px]"
                  style={{
                    borderColor: tableBorder,
                    color: tableRowText,
                  }}
                >
                  {item.portfolio}
                </td>
                <td 
                  className="border px-1 py-2 text-[18px]"
                  style={{
                    borderColor: tableBorder,
                    color: tableRowText,
                  }}
                >
                  {formatNumber(item.icApprovedBudget)}
                </td>
                <td 
                  className="border px-1 py-2 text-[18px]"
                  style={{
                    borderColor: tableBorder,
                    color: tableRowText,
                  }}
                >
                  {formatNumber(item.expectedBudget)}
                </td>
                <td 
                  className="border px-1 py-2 text-[18px]"
                  style={{
                    borderColor: tableBorder,
                    color: tableRowText,
                  }}
                >
                  {formatPercentage(item.difference)}
                </td>
                <td 
                  className="border px-1 py-2 text-[18px]"
                  style={{
                    borderColor: tableBorder,
                    color: tableRowTextSecondary,
                  }}
                >
                  {item.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div 
        className="shrink-0 rounded-lg border p-4 text-[18px] shadow-lg"
        style={{
          borderColor: noteBorder,
          background: noteBg,
          color: noteText,
        }}
      >
        <div className="mb-2 text-[20px] font-semibold" style={{ color: noteTitleText }}>📝 Note:</div>
        <div className="space-y-1 text-[18px]" style={{ color: noteTextSecondary }}>
          <div>
            1. Site wise data{' '}
            <a
              href="https://peakenergyasia.sharepoint.com/:x:/s/PeakEnergy-All/Eedf1mcnW4JPhythaFIGRF4B3I_ODUIrj5xOVcx2O0L8fw?e=Br943V"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:underline"
              style={{
                color: linkColor,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = linkHoverColor;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = linkColor;
              }}
            >
              IC Budget Vs Expected MTD.xlsx
            </a>
            .
          </div>
          <div>
            2. Asset No: 2,18,27,40 & 48 expected budgets are revised due to as built PV-syst is received in
            April-25.
          </div>
        </div>
      </div>
    </div>
  );
}

