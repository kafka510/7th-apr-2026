/**
 * Utility functions for sales data processing
 */

export function normalizeValue(value: string | number | null | undefined): string {
  if (value === undefined || value === null) return '';
  const str = String(value).trim();
  return str || '';
}

export function parseNumeric(value: string | number | null | undefined): number {
  if (value === undefined || value === null) return NaN;
  const str = String(value).trim();
  if (str === '' || str === 'null' || str === 'undefined' || str === 'None' || str === 'NaN') return NaN;
  const normalized = str.replace(/[\s,]/g, '');
  const match = normalized.match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : NaN;
}

export function normalizeMonth(val: string | null | undefined): string {
  if (!val) return '';
  const v = String(val).trim();
  // If already YYYY-MM
  if (/^\d{4}-\d{1,2}$/.test(v)) {
    const [y, m] = v.split('-');
    const month = m.padStart(2, '0');
    return `${y}-${month}`;
  }
  // If MM/YYYY or M/YYYY
  if (/^\d{1,2}\/\d{4}$/.test(v)) {
    const [m, y] = v.split('/');
    const month = m.padStart(2, '0');
    return `${y}-${month}`;
  }
  // If MonthName-YYYY or MonthName YYYY
  const match = v.match(/^(\w+)[-\s](\d{4})$/);
  if (match) {
    const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
    const idx = monthNames.indexOf(match[1].toLowerCase().slice(0, 3));
    if (idx >= 0) {
      return `${match[2]}-${String(idx + 1).padStart(2, '0')}`;
    }
  }
  // If only year, treat as Jan
  if (/^\d{4}$/.test(v)) {
    return `${v}-01`;
  }
  return v;
}

export function getMonthAbbr(ym: string | null | undefined): string {
  if (!ym) return '';
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const match = String(ym).match(/\d{4}-(\d{1,2})/);
  if (match) {
    const m = parseInt(match[1], 10);
    return monthNames[m - 1] || ym;
  }
  if (monthNames.some(name => String(ym).slice(0, 3) === name)) {
    return String(ym).slice(0, 3);
  }
  return String(ym);
}

