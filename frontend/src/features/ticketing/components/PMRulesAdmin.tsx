import { useState, useCallback, useEffect } from 'react';
import {
  fetchPMRules,
  fetchPMRule,
  createPMRule,
  updatePMRule,
  deletePMRule,
  togglePMRule,
  triggerPMProcessing,
  fetchTicketCategories,
} from '../api';
import type { PMRule, TicketCategory } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

type PMRulesAdminProps = {
  isSuperuser: boolean;
};

const DEVICE_DATE_FIELDS = [
  { value: 'equipment_warranty_start_date', label: 'Equipment Warranty Start Date' },
  { value: 'equipment_warranty_expire_date', label: 'Equipment Warranty Expire Date' },
  { value: 'epc_warranty_start_date', label: 'EPC Warranty Start Date' },
  { value: 'epc_warranty_expire_date', label: 'EPC Warranty Expire Date' },
  { value: 'cod', label: 'COD (from Asset List)' },
];

const DEVICE_FREQUENCY_FIELDS = [
  { value: 'calibration_frequency', label: 'Calibration Frequency' },
  { value: 'pm_frequency', label: 'PM Frequency' },
  { value: 'visual_inspection_frequency', label: 'Visual Inspection Frequency' },
];

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

export const PMRulesAdmin = ({ isSuperuser }: PMRulesAdminProps) => {
  const { theme } = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [rules, setRules] = useState<PMRule[]>([]);
  const [categories, setCategories] = useState<TicketCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Theme-aware colors
  const containerBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const headerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(51, 65, 85, 0.5)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';
  const textSecondary = theme === 'dark' ? '#94a3b8' : '#64748b';
  const textTertiary = theme === 'dark' ? '#64748b' : '#94a3b8';
  const formBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.9)';
  const formBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const inputFocusBorder = theme === 'dark' ? '#38bdf8' : '#0ea5e9';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const tableRowBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(248, 250, 252, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const tableDivider = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const deleteButtonBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.7)';
  const deleteButtonText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const deleteButtonHoverBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 0.9)';
  const toggleButtonBorder = theme === 'dark' ? 'rgba(245, 158, 11, 0.5)' : 'rgba(245, 158, 11, 0.7)';
  const toggleButtonText = theme === 'dark' ? '#fbbf24' : '#d97706';
  const toggleButtonHoverBg = theme === 'dark' ? 'rgba(120, 53, 15, 0.3)' : 'rgba(254, 243, 199, 0.9)';
  const activeBadgeBg = theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)';
  const activeBadgeText = theme === 'dark' ? '#6ee7b7' : '#059669';
  const inactiveBadgeBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.3)';
  const inactiveBadgeText = theme === 'dark' ? '#94a3b8' : '#475569';
  const dateBadgeBg = theme === 'dark' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(6, 182, 212, 0.1)';
  const dateBadgeText = theme === 'dark' ? '#67e8f9' : '#0891b2';
  const frequencyBadgeBg = theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)';
  const frequencyBadgeText = theme === 'dark' ? '#6ee7b7' : '#059669';
  const priorityBadgeBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const priorityBadgeText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 1)';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(254, 202, 202, 1)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#991b1b';
  const infoBg = theme === 'dark' ? 'rgba(147, 51, 234, 0.2)' : 'rgba(243, 232, 255, 1)';
  const infoBorder = theme === 'dark' ? 'rgba(147, 51, 234, 0.5)' : 'rgba(221, 214, 254, 1)';
  const infoText = theme === 'dark' ? '#c4b5fd' : '#6b21a8';
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'date_based' as 'date_based' | 'frequency_based',
    date_field_name: '',
    alert_days_before: 30,
    start_date_field: '',
    frequency_field: '',
    category: '',
    priority: 'medium',
    title_template: '',
    description_template: '',
    assign_to_role: '',
    send_email_notification: true,
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchPMRules();
      setRules(response.rules);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load PM rules');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const response = await fetchTicketCategories();
      setCategories(response.categories.filter((cat) => cat.is_active));
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  }, []);

  useEffect(() => {
    loadRules();
    loadCategories();
  }, [loadRules, loadCategories]);

  const handleCreate = () => {
    setEditingId(null);
    setFormData({
      name: '',
      description: '',
      rule_type: 'date_based',
      date_field_name: '',
      alert_days_before: 30,
      start_date_field: '',
      frequency_field: '',
      category: '',
      priority: 'medium',
      title_template: '',
      description_template: '',
      assign_to_role: '',
      send_email_notification: true,
      is_active: true,
    });
    setShowForm(true);
  };

  const handleEdit = async (id: number) => {
    try {
      const rule = await fetchPMRule(id);
      setEditingId(id);
      setFormData({
        name: rule.name,
        description: rule.description,
        rule_type: rule.rule_type,
        date_field_name: rule.date_field_name || '',
        alert_days_before: rule.alert_days_before || 30,
        start_date_field: rule.start_date_field || '',
        frequency_field: rule.frequency_field || '',
        category: rule.category?.id.toString() || '',
        priority: rule.priority,
        title_template: rule.title_template,
        description_template: rule.description_template,
        assign_to_role: rule.assign_to_role || '',
        send_email_notification: rule.send_email_notification,
        is_active: rule.is_active,
      });
      setShowForm(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rule');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const data = {
        name: formData.name,
        description: formData.description,
        rule_type: formData.rule_type,
        category: parseInt(formData.category),
        priority: formData.priority,
        title_template: formData.title_template,
        description_template: formData.description_template,
        send_email_notification: formData.send_email_notification,
        is_active: formData.is_active,
        alert_days_before: formData.rule_type === 'date_based' ? formData.alert_days_before : null,
        date_field_name: formData.rule_type === 'date_based' ? (formData.date_field_name || null) : null,
        start_date_field: formData.rule_type === 'frequency_based' ? (formData.start_date_field || null) : null,
        frequency_field: formData.rule_type === 'frequency_based' ? (formData.frequency_field || null) : null,
        assign_to_role: formData.assign_to_role || null,
      };

      if (editingId) {
        await updatePMRule(editingId, data);
      } else {
        await createPMRule(data);
      }
      setShowForm(false);
      setEditingId(null);
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save PM rule');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this PM rule? This will also delete all associated schedules. This action cannot be undone.')) {
      return;
    }

    try {
      await deletePMRule(id);
      await loadRules();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete PM rule';
      alert(message);
    }
  };

  const handleToggle = async (id: number) => {
    if (!window.confirm('Toggle active status for this rule?')) {
      return;
    }

    try {
      await togglePMRule(id);
      await loadRules();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to toggle PM rule';
      alert(message);
    }
  };

  const handleTrigger = async () => {
    if (!window.confirm('Trigger PM rule processing? This may take a few moments to complete.')) {
      return;
    }

    setTriggering(true);
    try {
      const result = await triggerPMProcessing();
      alert(result.message);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to trigger PM processing';
      alert(message);
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div 
        className="rounded-3xl border p-6 shadow-sm"
        style={{
          borderColor: containerBorder,
          background: containerBg,
        }}
      >
        <div className="text-center" style={{ color: textTertiary }}>Loading PM rules...</div>
      </div>
    );
  }

  return (
    <div 
      className="rounded-3xl border shadow-sm"
      style={{
        borderColor: containerBorder,
        background: containerBg,
      }}
    >
      <div 
        className="border-b bg-gradient-to-r from-purple-600 to-purple-700 px-6 py-4"
        style={{ borderColor: headerBorder }}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="bg-slate-700/50/10 hover:bg-slate-700/50/20 rounded border border-white/30 px-2 py-1 text-xs text-white transition"
            >
              {expanded ? '▼' : '▶'}
            </button>
            <h2 className="text-lg font-semibold text-white">Preventive Maintenance Rules</h2>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              className="rounded-lg bg-slate-700/50 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
            >
              + Create PM Rule
            </button>
            {isSuperuser && (
              <button
                onClick={handleTrigger}
                disabled={triggering}
                className="hover:bg-slate-700/50/20 rounded-lg border border-white bg-transparent px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
              >
                {triggering ? 'Running...' : 'Run PM Processing'}
              </button>
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="p-6">
        {error && !showForm && (
          <div 
            className="mb-4 rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: errorBorder,
              backgroundColor: errorBg,
              color: errorText,
            }}
          >
            {error}
          </div>
        )}

        {showForm && (
          <form 
            onSubmit={handleSubmit} 
            className="mb-6 rounded-lg border p-4"
            style={{
              borderColor: formBorder,
              backgroundColor: formBg,
            }}
          >
            <h3 className="mb-4 text-sm font-semibold" style={{ color: textPrimary }}>
              {editingId ? 'Edit PM Rule' : 'Create PM Rule'}
            </h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Rule Name <span style={{ color: errorText }}>*</span>
                </label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="e.g., Equipment Warranty Check"
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Description
                </label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Rule Type <span style={{ color: errorText }}>*</span>
                </label>
                <div className="mt-2 flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="date_based"
                      checked={formData.rule_type === 'date_based'}
                      onChange={(e) => setFormData({ ...formData, rule_type: e.target.value as 'date_based' | 'frequency_based' })}
                      className="size-4 focus:ring-2"
                      style={{
                        accentColor: theme === 'dark' ? '#38bdf8' : '#0ea5e9',
                      }}
                    />
                    <span className="text-sm" style={{ color: textPrimary }}>Date Based (Warranty/Expiry)</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      value="frequency_based"
                      checked={formData.rule_type === 'frequency_based'}
                      onChange={(e) => setFormData({ ...formData, rule_type: e.target.value as 'date_based' | 'frequency_based' })}
                      className="size-4 focus:ring-2"
                      style={{
                        accentColor: theme === 'dark' ? '#38bdf8' : '#0ea5e9',
                      }}
                    />
                    <span className="text-sm" style={{ color: textPrimary }}>Frequency Based (Recurring)</span>
                  </label>
                </div>
              </div>

              {formData.rule_type === 'date_based' ? (
                <>
                  <div>
                    <label htmlFor="date_field_name" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                      Expiry Date Field <span style={{ color: errorText }}>*</span>
                    </label>
                    <select
                      id="date_field_name"
                      value={formData.date_field_name}
                      onChange={(e) => setFormData({ ...formData, date_field_name: e.target.value })}
                      required
                      className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                      style={{
                        borderColor: inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = inputFocusBorder;
                        e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = inputBorder;
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <option value="">-- Select Field --</option>
                      {DEVICE_DATE_FIELDS.map((field) => (
                        <option key={field.value} value={field.value}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="alert_days_before" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                      Alert Days Before <span style={{ color: errorText }}>*</span>
                    </label>
                    <input
                      type="number"
                      id="alert_days_before"
                      value={formData.alert_days_before}
                      onChange={(e) => setFormData({ ...formData, alert_days_before: parseInt(e.target.value) || 0 })}
                      required
                      min={1}
                      max={365}
                      className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                      style={{
                        borderColor: inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = inputFocusBorder;
                        e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = inputBorder;
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label htmlFor="start_date_field" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                      Start Date Field <span style={{ color: errorText }}>*</span>
                    </label>
                    <select
                      id="start_date_field"
                      value={formData.start_date_field}
                      onChange={(e) => setFormData({ ...formData, start_date_field: e.target.value })}
                      required
                      className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                      style={{
                        borderColor: inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = inputFocusBorder;
                        e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = inputBorder;
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <option value="">-- Select Field --</option>
                      {DEVICE_DATE_FIELDS.map((field) => (
                        <option key={field.value} value={field.value}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="frequency_field" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                      Frequency Field <span style={{ color: errorText }}>*</span>
                    </label>
                    <select
                      id="frequency_field"
                      value={formData.frequency_field}
                      onChange={(e) => setFormData({ ...formData, frequency_field: e.target.value })}
                      required
                      className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                      style={{
                        borderColor: inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = inputFocusBorder;
                        e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = inputBorder;
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <option value="">-- Select Field --</option>
                      {DEVICE_FREQUENCY_FIELDS.map((field) => (
                        <option key={field.value} value={field.value}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              <div>
                <label htmlFor="category" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Ticket Category <span style={{ color: errorText }}>*</span>
                </label>
                <select
                  id="category"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  required
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <option value="">-- Select Category --</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="priority" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Priority <span style={{ color: errorText }}>*</span>
                </label>
                <select
                  id="priority"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  required
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {PRIORITY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="title_template" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Ticket Title Template <span style={{ color: errorText }}>*</span>
                </label>
                <input
                  type="text"
                  id="title_template"
                  value={formData.title_template}
                  onChange={(e) => setFormData({ ...formData, title_template: e.target.value })}
                  required
                  placeholder="PM: {rule_name} - {device_name} at {site_name}"
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
                <p className="mt-1 text-xs" style={{ color: textSecondary }}>
                  Use placeholders: {'{rule_name}'}, {'{device_name}'}, {'{site_name}'}, {'{date}'}
                </p>
              </div>

              <div>
                <label htmlFor="description_template" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Ticket Description Template <span style={{ color: errorText }}>*</span>
                </label>
                <textarea
                  id="description_template"
                  value={formData.description_template}
                  onChange={(e) => setFormData({ ...formData, description_template: e.target.value })}
                  required
                  rows={4}
                  placeholder="This is an automated preventive maintenance ticket for {device_name}..."
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
                <p className="mt-1 text-xs" style={{ color: textSecondary }}>Use same placeholders as title</p>
              </div>

              <div>
                <label htmlFor="assign_to_role" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Auto-assign To Role
                </label>
                <input
                  type="text"
                  id="assign_to_role"
                  value={formData.assign_to_role}
                  onChange={(e) => setFormData({ ...formData, assign_to_role: e.target.value })}
                  placeholder="e.g., management, om, admin (leave empty for no auto-assignment)"
                  className="mt-1 w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2"
                  style={{
                    borderColor: inputBorder,
                    backgroundColor: inputBg,
                    color: inputText,
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = inputFocusBorder;
                    e.currentTarget.style.boxShadow = `0 0 0 1px ${inputFocusBorder}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = inputBorder;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
              </div>

              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.send_email_notification}
                    onChange={(e) => setFormData({ ...formData, send_email_notification: e.target.checked })}
                    className="size-4 rounded"
                    style={{
                      accentColor: theme === 'dark' ? '#38bdf8' : '#0ea5e9',
                    }}
                  />
                  <span className="text-sm font-semibold" style={{ color: textPrimary }}>Send Email Notification</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="size-4 rounded"
                    style={{
                      accentColor: theme === 'dark' ? '#38bdf8' : '#0ea5e9',
                    }}
                  />
                  <span className="text-sm font-semibold" style={{ color: textPrimary }}>Active</span>
                </label>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                  style={{
                    backgroundColor: theme === 'dark' ? 'rgba(147, 51, 234, 0.8)' : '#9333ea',
                  }}
                  onMouseEnter={(e) => {
                    if (!submitting) {
                      e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(147, 51, 234, 1)' : '#7e22ce';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!submitting) {
                      e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(147, 51, 234, 0.8)' : '#9333ea';
                    }
                  }}
                >
                  {submitting ? 'Saving...' : editingId ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setEditingId(null);
                    setError(null);
                  }}
                  className="rounded-lg border px-4 py-2 text-sm font-semibold transition"
                  style={{
                    borderColor: buttonBorder,
                    backgroundColor: buttonBg,
                    color: buttonText,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = buttonHoverBg;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = buttonBg;
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        )}

        {rules.length === 0 ? (
          <div 
            className="rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: infoBorder,
              backgroundColor: infoBg,
              color: infoText,
            }}
          >
            No preventive maintenance rules defined yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table 
              className="min-w-full divide-y text-sm"
              style={{ borderColor: tableDivider }}
            >
              <thead style={{ backgroundColor: tableHeaderBg }}>
                <tr>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Rule Name
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Type
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Category
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Priority
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Status
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Created By
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody 
                className="divide-y"
                style={{ 
                  borderColor: tableDivider,
                  backgroundColor: tableRowBg,
                }}
              >
                {rules.map((rule) => (
                  <tr 
                    key={rule.id}
                    style={{
                      borderColor: tableDivider,
                      backgroundColor: tableRowBg,
                      color: tableRowText,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = tableRowHoverBg;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = tableRowBg;
                    }}
                  >
                    <td className="p-4">
                      <div className="font-semibold" style={{ color: tableRowText }}>{rule.name}</div>
                      {rule.description && (
                        <div className="mt-1 text-xs" style={{ color: textSecondary }}>{rule.description.substring(0, 50)}...</div>
                      )}
                    </td>
                    <td className="p-4">
                      {rule.rule_type === 'date_based' ? (
                        <div>
                          <span 
                            className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold"
                            style={{
                              backgroundColor: dateBadgeBg,
                              color: dateBadgeText,
                            }}
                          >
                            Date Based
                          </span>
                          {rule.date_field_name && (
                            <div className="mt-1 text-xs" style={{ color: textSecondary }}>{rule.date_field_name}</div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <span 
                            className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold"
                            style={{
                              backgroundColor: frequencyBadgeBg,
                              color: frequencyBadgeText,
                            }}
                          >
                            Frequency Based
                          </span>
                          {rule.frequency_field && (
                            <div className="mt-1 text-xs" style={{ color: textSecondary }}>{rule.frequency_field}</div>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="p-4" style={{ color: textSecondary }}>{rule.category?.name || '—'}</td>
                    <td className="p-4">
                      <span 
                        className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: priorityBadgeBg,
                          color: priorityBadgeText,
                        }}
                      >
                        {rule.priority_display}
                      </span>
                    </td>
                    <td className="p-4">
                      {rule.is_active ? (
                        <span 
                          className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold"
                          style={{
                            backgroundColor: activeBadgeBg,
                            color: activeBadgeText,
                          }}
                        >
                          Active
                        </span>
                      ) : (
                        <span 
                          className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold"
                          style={{
                            backgroundColor: inactiveBadgeBg,
                            color: inactiveBadgeText,
                          }}
                        >
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="p-4" style={{ color: textSecondary }}>{rule.created_by?.username || '—'}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(rule.id)}
                          className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                          style={{
                            borderColor: buttonBorder,
                            backgroundColor: buttonBg,
                            color: buttonText,
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = buttonHoverBg;
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = buttonBg;
                          }}
                          title="Edit"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleToggle(rule.id)}
                          className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                          style={{
                            borderColor: toggleButtonBorder,
                            backgroundColor: buttonBg,
                            color: toggleButtonText,
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = toggleButtonHoverBg;
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = buttonBg;
                          }}
                          title="Toggle Active Status"
                        >
                          Toggle
                        </button>
                        {isSuperuser && (
                          <button
                            onClick={() => handleDelete(rule.id)}
                            className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                            style={{
                              borderColor: deleteButtonBorder,
                              backgroundColor: buttonBg,
                              color: deleteButtonText,
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = deleteButtonHoverBg;
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = buttonBg;
                            }}
                            title="Delete"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        </div>
      )}
    </div>
  );
};

