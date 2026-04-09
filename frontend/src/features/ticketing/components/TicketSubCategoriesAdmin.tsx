import { useState, useCallback, useEffect } from 'react';

import {
  fetchTicketSubCategories,
  fetchTicketCategories,
  createTicketSubCategory,
  updateTicketSubCategory,
  deleteTicketSubCategory,
} from '../api';
import type { TicketCategory, TicketSubCategory } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

type TicketSubCategoriesAdminProps = {
  isSuperuser: boolean;
};

export const TicketSubCategoriesAdmin = ({ isSuperuser }: TicketSubCategoriesAdminProps) => {
  const { theme } = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [subCategories, setSubCategories] = useState<TicketSubCategory[]>([]);
  const [categories, setCategories] = useState<TicketCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<number | 'all'>('all');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    display_order: 0,
    is_active: true,
    category: '',
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
  const inputFocusBorder = theme === 'dark' ? '#38bdf8' : '#6366f1';
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
  const infoBg = theme === 'dark' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(238, 242, 255, 1)';
  const infoBorder = theme === 'dark' ? 'rgba(99, 102, 241, 0.5)' : 'rgba(199, 210, 254, 1)';
  const infoText = theme === 'dark' ? '#a5b4fc' : '#4338ca';
  const selectBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const selectBorder = theme === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(203, 213, 225, 0.8)';
  const selectText = theme === 'dark' ? '#ffffff' : '#1e293b';
  const selectHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [subResponse, categoryResponse] = await Promise.all([
        fetchTicketSubCategories(undefined, selectedCategory === 'all' ? undefined : selectedCategory),
        fetchTicketCategories(),
      ]);
      setSubCategories(subResponse.subCategories);
      setCategories(categoryResponse.categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sub-categories');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = () => {
    setEditingId(null);
    setFormData({
      name: '',
      description: '',
      display_order: 0,
      is_active: true,
      category: selectedCategory === 'all' ? '' : String(selectedCategory),
    });
    setShowForm(true);
  };

  const handleEdit = (subCategory: TicketSubCategory) => {
    setEditingId(subCategory.id);
    setFormData({
      name: subCategory.name,
      description: subCategory.description,
      display_order: subCategory.display_order,
      is_active: subCategory.is_active,
      category: subCategory.category ? String(subCategory.category.id) : '',
    });
    setShowForm(true);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!formData.category) {
      setError('Category is required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        display_order: formData.display_order,
        is_active: formData.is_active,
        category: Number(formData.category),
      };
      if (editingId) {
        await updateTicketSubCategory(editingId, payload);
      } else {
        await createTicketSubCategory(payload);
      }
      setShowForm(false);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save sub-category');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this sub-category? Tickets using this sub-category will be updated to remove it.',
      )
    ) {
      return;
    }

    try {
      const result = await deleteTicketSubCategory(id);
      await loadData();
      if (result.message) {
        alert(result.message);
      }
    } catch (err) {
      let message = 'Failed to delete sub-category';
      if (err instanceof Error) {
        try {
          const data = JSON.parse(err.message);
          message = data.detail || data.message || err.message;
        } catch {
          message = err.message;
        }
      }
      setError(message);
      alert(message);
    }
  };

  const filteredSubCategories =
    selectedCategory === 'all'
      ? subCategories
      : subCategories.filter((sub) => sub.category?.id === selectedCategory);

  if (loading) {
    return (
      <div 
        className="rounded-3xl border p-6 shadow-sm"
        style={{
          borderColor: containerBorder,
          background: containerBg,
        }}
      >
        <div className="text-center" style={{ color: textTertiary }}>Loading sub-categories...</div>
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
        className="border-b bg-gradient-to-r from-indigo-500 to-indigo-600 px-6 py-4"
        style={{ borderColor: headerBorder }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="bg-slate-700/50/10 hover:bg-slate-700/50/20 rounded border border-white/30 px-2 py-1 text-xs text-white transition"
            >
              {expanded ? '▼' : '▶'}
            </button>
            <h2 className="text-lg font-semibold text-white">Ticket Sub-Categories</h2>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value === 'all' ? 'all' : Number(event.target.value))}
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
              style={{
                borderColor: selectBorder,
                backgroundColor: selectBg,
                color: selectText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = selectHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = selectBg;
              }}
            >
              <option value="all" style={{ backgroundColor: inputBg, color: inputText }}>All Categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id} style={{ backgroundColor: inputBg, color: inputText }}>
                  {category.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleCreate}
              className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition"
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(99, 102, 241, 0.1)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(99, 102, 241, 0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(99, 102, 241, 0.1)';
              }}
            >
              + Create Sub-Category
            </button>
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
              <h3 className="mb-4 text-sm font-semibold" style={{ color: textPrimary }}>{editingId ? 'Edit Sub-Category' : 'Create Sub-Category'}</h3>
              <div className="space-y-4">
                <div>
                  <label htmlFor="sub-category-name" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                    Name <span style={{ color: errorText }}>*</span>
                  </label>
                  <input
                    type="text"
                    id="sub-category-name"
                    value={formData.name}
                    onChange={(event) => setFormData({ ...formData, name: event.target.value })}
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
                  <label htmlFor="sub-category-category" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                    Parent Category <span style={{ color: errorText }}>*</span>
                  </label>
                  <select
                    id="sub-category-category"
                    value={formData.category}
                    onChange={(event) => setFormData({ ...formData, category: event.target.value })}
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
                    <option value="">Select category</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="sub-category-description" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                    Description
                  </label>
                  <textarea
                    id="sub-category-description"
                    value={formData.description}
                    onChange={(event) => setFormData({ ...formData, description: event.target.value })}
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
                    <label htmlFor="sub-category-order" className="block text-sm font-semibold" style={{ color: textPrimary }}>
                      Display Order
                    </label>
                    <input
                      type="number"
                      id="sub-category-order"
                      value={formData.display_order}
                      onChange={(event) =>
                        setFormData({ ...formData, display_order: Number.isNaN(event.target.valueAsNumber) ? 0 : event.target.valueAsNumber })
                      }
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
                        onChange={(event) => setFormData({ ...formData, is_active: event.target.checked })}
                        className="size-4 rounded"
                        style={{
                          accentColor: theme === 'dark' ? '#6366f1' : '#4f46e5',
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
                      backgroundColor: theme === 'dark' ? 'rgba(99, 102, 241, 0.8)' : '#4f46e5',
                    }}
                    onMouseEnter={(e) => {
                      if (!submitting) {
                        e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(99, 102, 241, 1)' : '#4338ca';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!submitting) {
                        e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(99, 102, 241, 0.8)' : '#4f46e5';
                      }
                    }}
                  >
                    {submitting ? 'Saving…' : editingId ? 'Update' : 'Create'}
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

          {filteredSubCategories.length === 0 ? (
            <div 
              className="rounded-lg border px-4 py-3 text-sm"
              style={{
                borderColor: infoBorder,
                backgroundColor: infoBg,
                color: infoText,
              }}
            >
              No sub-categories found.
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
                      Category
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
                  {filteredSubCategories.map((sub) => (
                    <tr 
                      key={sub.id}
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
                      <td className="p-4 font-semibold" style={{ color: tableRowText }}>{sub.name}</td>
                      <td className="p-4" style={{ color: textSecondary }}>{sub.category?.name ?? '—'}</td>
                      <td className="p-4" style={{ color: textSecondary }}>{sub.display_order}</td>
                      <td className="p-4">
                        {sub.is_active ? (
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
                            onClick={() => handleEdit(sub)}
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
                              onClick={() => handleDelete(sub.id)}
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


