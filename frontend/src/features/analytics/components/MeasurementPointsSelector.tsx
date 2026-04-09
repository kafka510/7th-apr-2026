/**
 * Measurement Points Selector Component
 */
 
import { useState, useMemo } from 'react';
import type { MeasurementPointsByDeviceType, MeasurementPointsDiagnostics } from '../types';

interface MeasurementPointsSelectorProps {
  measurementPoints: MeasurementPointsByDeviceType;
  selectedMetrics: string[];
  onMetricsChange: (metrics: string[]) => void;
  loading?: boolean;
  error?: string | null;
  diagnostics?: MeasurementPointsDiagnostics | null;
}

function DiagnosticsPanel({ diagnostics }: { diagnostics: MeasurementPointsDiagnostics }) {
  const rows: { label: string; value: string }[] = [
    { label: 'Lookup codes', value: diagnostics.lookup_codes?.length ? diagnostics.lookup_codes.join(', ') : '—' },
    {
      label: 'Device types (requested)',
      value: diagnostics.device_types_requested?.length ? diagnostics.device_types_requested.join(', ') : '—',
    },
    {
      label: 'Device types (expanded)',
      value: diagnostics.expanded_device_types?.length ? diagnostics.expanded_device_types.join(', ') : '—',
    },
    { label: 'Mapping rows matched', value: String(diagnostics.raw_mapping_row_count ?? 0) },
    { label: 'Rows with metric name', value: String(diagnostics.rows_with_nonempty_metric ?? 0) },
    { label: 'Distinct metrics', value: String(diagnostics.grouped_metric_count ?? 0) },
    {
      label: 'Type filter fallback',
      value: diagnostics.used_device_type_fallback ? 'Yes (broadened search)' : 'No',
    },
  ];

  return (
    <div className="mt-3 rounded border border-amber-200 bg-amber-50/80 p-3 text-sm text-slate-800">
      <div className="mb-2 font-semibold text-amber-900">Why metrics may be missing</div>
      {diagnostics.hints?.length ? (
        <ul className="mb-3 list-inside list-disc space-y-1 text-slate-800">
          {diagnostics.hints.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      ) : null}
      <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
        {rows.map(({ label, value }) => (
          <div key={label} className="contents">
            <dt className="font-medium text-slate-600">{label}</dt>
            <dd className="mb-1 sm:mb-0">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function MeasurementPointsSelector({
  measurementPoints,
  selectedMetrics,
  onMetricsChange,
  loading = false,
  error = null,
  diagnostics = null,
}: MeasurementPointsSelectorProps) {
  const getUniqueMetrics = (
    measurements: Array<{ metric: string; units?: string; description?: string; oem_tag?: string }>
  ) => {
    const uniqueMetrics = new Map();
    measurements.forEach((mp) => {
      if (!mp?.metric || mp.metric.trim() === '') {
        return;
      }
      const metricKey = mp.metric;
      if (
        !uniqueMetrics.has(metricKey) ||
        (mp.units && !uniqueMetrics.get(metricKey).units) ||
        (mp.description && !uniqueMetrics.get(metricKey).description)
      ) {
        uniqueMetrics.set(metricKey, mp);
      }
    });
    return Array.from(uniqueMetrics.values());
  };

  // Track which groups the user has manually collapsed
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // Compute available groups from measurement points
  const availableGroups = useMemo(() => {
    return Object.keys(measurementPoints)
      .filter((deviceType) => {
        const rows = measurementPoints[deviceType];
        return Array.isArray(rows) && getUniqueMetrics(rows).length > 0;
      })
      .sort();
  }, [measurementPoints]);

  // Compute expanded groups: all available groups minus manually collapsed ones
  const expandedGroups = useMemo(() => {
    const expanded = new Set(availableGroups);
    collapsedGroups.forEach((group) => expanded.delete(group));
    return expanded;
  }, [availableGroups, collapsedGroups]);

  const toggleGroup = (deviceType: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(deviceType)) {
        next.delete(deviceType);
      } else {
        next.add(deviceType);
      }
      return next;
    });
  };

  const handleMetricToggle = (metric: string, checked: boolean) => {
    if (checked) {
      onMetricsChange([...selectedMetrics, metric]);
    } else {
      onMetricsChange(selectedMetrics.filter((m) => m !== metric));
    }
  };

  const hasGroups = availableGroups.length > 0;

  if (!hasGroups) {
    return (
      <div className="mb-4">
        <label className="mb-2 block text-sm font-bold text-slate-900">
          Select Measurement Points
        </label>
        {loading ? (
          <div className="flex items-center gap-2 font-medium text-slate-600">
            Loading measurement points…
          </div>
        ) : error ? (
          <div
            className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900"
            role="alert"
          >
            <span className="font-semibold">Could not load metrics. </span>
            {error}
          </div>
        ) : (
          <div className="font-medium text-slate-700">
            No measurement points found for the selected devices. Check device mapping and that incoming data includes metric names.
          </div>
        )}
        {!loading && diagnostics ? <DiagnosticsPanel diagnostics={diagnostics} /> : null}
      </div>
    );
  }

  return (
    <div className="mb-4">
      <label className="mb-2 block text-sm font-semibold text-slate-700">
        Select Measurement Points
      </label>
      {loading ? (
        <div className="mb-2 flex items-center gap-2 text-sm text-slate-600">
          Refreshing measurement points…
        </div>
      ) : null}
      {error ? (
        <div
          className="mb-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-900"
          role="alert"
        >
          {error}
        </div>
      ) : null}
      {diagnostics?.hints?.length ? (
        <div className="mb-2 text-xs text-amber-900">
          <span className="font-semibold">Note: </span>
          {diagnostics.hints.join(' ')}
        </div>
      ) : null}
      <div className="space-y-3">
        {availableGroups.map((deviceType) => {
            const isExpanded = expandedGroups.has(deviceType);
            const groupRows = Array.isArray(measurementPoints[deviceType]) ? measurementPoints[deviceType] : [];
            const uniqueMetrics = getUniqueMetrics(groupRows);

            return (
              <div key={deviceType} className="rounded border-2 border-slate-200 bg-white p-4">
                <div
                  className="mb-3 flex cursor-pointer items-center justify-between"
                  onClick={() => toggleGroup(deviceType)}
                >
                  <h5 className="m-0 text-sm font-bold text-slate-900">
                    {deviceType || 'Unknown device type'}
                  </h5>
                </div>

                {isExpanded && (
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
                    {uniqueMetrics.map((mp) => {
                      const metricKey = mp.metric;
                      const isChecked = selectedMetrics.includes(metricKey);
                      const displayText = `${mp.metric}${mp.units ? ` (${mp.units})` : ''}`;

                      return (
                        <div
                          key={metricKey}
                          className="flex items-center rounded bg-slate-50 p-2 transition-colors hover:bg-slate-100"
                        >
                          <input
                            type="checkbox"
                            id={`mp-${deviceType}-${metricKey}`}
                            className="mr-2 size-4 cursor-pointer"
                            checked={isChecked}
                            onChange={(e) => handleMetricToggle(metricKey, e.target.checked)}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <label
                            htmlFor={`mp-${deviceType}-${metricKey}`}
                            className="flex-1 cursor-pointer text-sm font-medium text-slate-900"
                            title={mp.description || mp.metric}
                          >
                            {displayText}
                          </label>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
      </div>
      <small className="mt-2 block font-medium text-slate-700">
        <span>{selectedMetrics.length}</span> measurement point(s) selected
      </small>
    </div>
  );
}

