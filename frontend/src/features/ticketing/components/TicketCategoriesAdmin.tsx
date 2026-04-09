import { useState, useCallback, useEffect } from 'react';
import {
  fetchTicketCategories,
  createTicketCategory,
  updateTicketCategory,
  deleteTicketCategory,
} from '../api';
import type { TicketCategory } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

type TicketCategoriesAdminProps = {
  isSuperuser: boolean;
};

export const TicketCategoriesAdmin = ({ isSuperuser }: TicketCategoriesAdminProps) => {
  const { theme } = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [categories, setCategories] = useState<TicketCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    display_order: 0,
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);

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
  const activeBadgeBg = theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)';
  const activeBadgeText = theme === 'dark' ? '#6ee7b7' : '#059669';
  const inactiveBadgeBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.3)';
  const inactiveBadgeText = theme === 'dark' ? '#94a3b8' : '#475569';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 1)';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(254, 202, 202, 1)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#991b1b';
  const infoBg = theme === 'dark' ? 'rgba(14, 165, 233, 0.2)' : 'rgba(224, 242, 254, 1)';
  const infoBorder = theme === 'dark' ? 'rgba(14, 165, 233, 0.5)' : 'rgba(186, 230, 253, 1)';
  const infoText = theme === 'dark' ? '#7dd3fc' : '#0c4a6e';

  const loadCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTicketCategories();
      setCategories(response.categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load categories');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleCreate = () => {
    setEditingId(null);
    setFormData({
      name: '',
      description: '',
      display_order: 0,
      is_active: true,
    });
    setShowForm(true);
  };

  const handleEdit = (category: TicketCategory) => {
    setEditingId(category.id);
    setFormData({
      name: category.name,
      description: category.description,
      display_order: category.display_order,
      is_active: category.is_active,
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (editingId) {
        await updateTicketCategory(editingId, formData);
      } else {
        await createTicketCategory(formData);
      }
      setShowForm(false);
      setEditingId(null);
      await loadCategories();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save category');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this category? Tickets using this category will be reassigned to another category.')) {
      return;
    }

    try {
      const result = await deleteTicketCategory(id);
      await loadCategories();
      setError(null);
      // Show success message
      if (result.message) {
        alert(result.message);
      }
    } catch (err) {
      let message = 'Failed to delete category';
      if (err instanceof Error) {
        // Try to parse JSON error response
        try {
          const errorData = JSON.parse(err.message);
          message = errorData.detail || errorData.message || err.message;
        } catch {
          // If not JSON, use the error message as-is
          message = err.message;
        }
      }
      setError(message);
      alert(message);
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
        <div className="text-center" style={{ color: textTertiary }}>Loading categories...</div>
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
        className="border-b bg-gradient-to-r from-sky-600 to-sky-700 px-6 py-4"
        style={{ borderColor: headerBorder }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="rounded border border-white/30 bg-white/10 px-2 py-1 text-xs text-white transition hover:bg-white/20"
            >
              {expanded ? '▼' : '▶'}
            </button>
            <h2 className="text-lg font-semibold text-white">Ticket Categories</h2>
          </div>
          <button
            onClick={handleCreate}
            className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
          >
            + Create Category
          </button>
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
              {editingId ? 'Edit Category' : 'Create Category'}
            </h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                  Name <span style={{ color: errorText }}>*</span>
                </label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
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
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="display_order" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                    Display Order
                  </label>
                  <input
                    type="number"
                    id="display_order"
                    value={formData.display_order}
                    onChange={(e) => setFormData({ ...formData, display_order: parseInt(e.target.value) || 0 })}
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
                <div className="flex items-center pt-8">
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
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                  style={{
                    backgroundColor: theme === 'dark' ? 'rgba(14, 165, 233, 0.8)' : '#0284c7',
                  }}
                  onMouseEnter={(e) => {
                    if (!submitting) {
                      e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(14, 165, 233, 1)' : '#0369a1';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!submitting) {
                      e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(14, 165, 233, 0.8)' : '#0284c7';
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

        {categories.length === 0 ? (
          <div 
            className="rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: infoBorder,
              backgroundColor: infoBg,
              color: infoText,
            }}
          >
            No ticket categories found.{' '}
            <button 
              onClick={handleCreate} 
              className="font-semibold underline"
              style={{ color: infoText }}
            >
              Create one now
            </button>
            .
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
                    Name
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Description
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: tableHeaderText }}
                  >
                    Display Order
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
                {categories.map((category) => (
                  <tr 
                    key={category.id}
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
                    <td className="p-4 font-semibold" style={{ color: tableRowText }}>{category.name}</td>
                    <td className="p-4" style={{ color: textSecondary }}>{category.description || '—'}</td>
                    <td className="p-4" style={{ color: textSecondary }}>{category.display_order}</td>
                    <td className="p-4">
                      {category.is_active ? (
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
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(category)}
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
                        >
                          Edit
                        </button>
                        {isSuperuser && (
                          <button
                            onClick={() => handleDelete(category.id)}
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

