import type { KpiMetric } from '../types';

// CSV export for KPI Gauges data (asset-wise)
 
export const exportKpiGaugesToCSV = (metrics: KpiMetric[]): void => {
  if (!metrics || metrics.length === 0) {
    window.alert('No KPI gauge data available to export for the current filters.');
    return;
  }

  const headers = [
    'Asset Number',
    'Asset Code',
    'Asset Name',
    'Country',
    'Portfolio',
    'Date',
    'Daily IC Budget (MWh)',
    'Daily Expected (MWh)',
    'Daily Generation (MWh)',
    'Daily Budget Irradiation (MWh/m²)',
    'Daily Actual Irradiation (MWh/m²)',
    'Expected PR',
    'Actual PR',
    'Capacity (MW)',
    'DC Capacity (MW)',
    'Site State',
    'Last Updated',
  ];

  const csvRows: string[] = [];
  csvRows.push(headers.join(','));

  const escape = (value: unknown): string => {
    if (value === null || value === undefined) {
      return '';
    }
    const str = String(value);
    // Wrap in quotes and escape any embedded quotes
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  metrics.forEach((m) => {
    const row = [
      escape(m.asset_number),
      escape(m.asset_code),
      escape(m.asset_name),
      escape(m.country),
      escape(m.portfolio),
      // Use YYYY-MM-DD from date field
      escape(m.date ? m.date.slice(0, 10) : ''),
      // Energy and irradiation values
      escape(
        m.daily_ic_mwh !== undefined && m.daily_ic_mwh !== null
          ? Number(m.daily_ic_mwh).toString()
          : '',
      ),
      escape(
        m.daily_expected_mwh !== undefined && m.daily_expected_mwh !== null
          ? Number(m.daily_expected_mwh).toString()
          : '',
      ),
      escape(
        m.daily_generation_mwh !== undefined && m.daily_generation_mwh !== null
          ? Number(m.daily_generation_mwh).toString()
          : '',
      ),
      escape(
        m.daily_budget_irradiation_mwh !== undefined &&
          m.daily_budget_irradiation_mwh !== null
          ? Number(m.daily_budget_irradiation_mwh).toString()
          : '',
      ),
      escape(
        m.daily_irradiation_mwh !== undefined && m.daily_irradiation_mwh !== null
          ? Number(m.daily_irradiation_mwh).toString()
          : '',
      ),
      // PR values (as raw decimals, e.g. 0.82 for 82%)
      escape(
        m.expect_pr !== undefined && m.expect_pr !== null
          ? Number(m.expect_pr).toString()
          : '',
      ),
      escape(
        m.actual_pr !== undefined && m.actual_pr !== null
          ? Number(m.actual_pr).toString()
          : '',
      ),
      escape(
        m.capacity !== undefined && m.capacity !== null
          ? Number(m.capacity).toString()
          : '',
      ),
      escape(
        m.dc_capacity_mw !== undefined && m.dc_capacity_mw !== null
          ? Number(m.dc_capacity_mw).toString()
          : '',
      ),
      escape(m.site_state ?? ''),
      escape(m.last_updated ?? ''),
    ];

    csvRows.push(row.join(','));
  });

  const csvContent = csvRows.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  const todayStr = new Date().toISOString().slice(0, 10);
  link.href = url;
  link.download = `KPI_Gauges_${todayStr}.csv`;
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
};

