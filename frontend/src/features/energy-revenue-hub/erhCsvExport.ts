type Row = Record<string, unknown>;

/** Minimal shape for deriving a filename hint (avoids circular import with SessionDataTabs). */
export type ErhBundleLike = {
  utility_invoices?: Row[];
  line_items?: Row[];
  parsed_invoices?: Row[];
  generated_invoices?: Row[];
  payments?: Row[];
};

export function formatCellCsv(v: unknown): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'object') {
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  }
  return String(v);
}

function csvEscapeField(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/** Column order: preferred keys that exist in data first, then remaining keys sorted. */
export function buildColumnOrder(rows: Row[], preferred: string[]): string[] {
  const keys = new Set<string>();
  for (const r of rows) {
    for (const k of Object.keys(r)) keys.add(k);
  }
  const seen = new Set<string>();
  const out: string[] = [];
  for (const k of preferred) {
    if (keys.has(k) && !seen.has(k)) {
      out.push(k);
      seen.add(k);
    }
  }
  for (const k of [...keys].sort()) {
    if (!seen.has(k)) out.push(k);
  }
  return out;
}

export function rowsToCsv(rows: Row[], preferred: string[]): string {
  if (rows.length === 0) return '';
  const cols = buildColumnOrder(rows, preferred);
  const header = cols.map((c) => csvEscapeField(c)).join(',');
  const lines = rows.map((row) => cols.map((c) => csvEscapeField(formatCellCsv(row[c]))).join(','));
  return [header, ...lines].join('\r\n');
}

export function billingSessionIdForFilename(bundle: ErhBundleLike): string {
  const pick = (rows: Row[] | undefined) => rows?.[0]?.billing_session_id;
  const raw =
    pick(bundle.utility_invoices) ||
    pick(bundle.line_items) ||
    pick(bundle.parsed_invoices) ||
    pick(bundle.generated_invoices) ||
    pick(bundle.payments);
  const s = String(raw ?? '')
    .replace(/[^a-zA-Z0-9_-]/g, '')
    .slice(0, 14);
  return s || 'session';
}

export function triggerCsvDownload(filename: string, csvContent: string): void {
  const blob = new Blob([`\uFEFF${csvContent}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
