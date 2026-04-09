import { useState } from 'react';

import {
  createTicketManpower,
  createTicketMaterial,
  deleteTicketManpower,
  deleteTicketMaterial,
  updateTicketManpower,
  updateTicketMaterial,
} from '../api';
import type { TicketManpowerEntry, TicketMaterialEntry } from '../types';

type TicketResourcesProps = {
  ticketId: string;
  materials: TicketMaterialEntry[];
  manpower: TicketManpowerEntry[];
  canEdit: boolean;
  canDelete: boolean;
  onUpdate: () => void;
};

type MaterialFormState = {
  material_name: string;
  quantity: string;
  unit_price: string;
};

type ManpowerFormState = {
  person_name: string;
  hours_worked: string;
  hourly_rate: string;
};

const initialMaterialState: MaterialFormState = {
  material_name: '',
  quantity: '',
  unit_price: '',
};

const initialManpowerState: ManpowerFormState = {
  person_name: '',
  hours_worked: '',
  hourly_rate: '',
};

export const TicketResources = ({ ticketId, materials, manpower, canEdit, canDelete, onUpdate }: TicketResourcesProps) => {
  const [materialForm, setMaterialForm] = useState<MaterialFormState>(initialMaterialState);
  const [editingMaterialId, setEditingMaterialId] = useState<string | null>(null);
  const [manpowerForm, setManpowerForm] = useState<ManpowerFormState>(initialManpowerState);
  const [editingManpowerId, setEditingManpowerId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetMaterialForm = () => {
    setMaterialForm(initialMaterialState);
    setEditingMaterialId(null);
  };

  const resetManpowerForm = () => {
    setManpowerForm(initialManpowerState);
    setEditingManpowerId(null);
  };

  const handleMaterialSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canEdit) return;
    if (!materialForm.material_name || !materialForm.quantity || !materialForm.unit_price) {
      setError('Please fill in material name, quantity, and unit price.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (editingMaterialId) {
        await updateTicketMaterial(ticketId, editingMaterialId, {
          material_name: materialForm.material_name,
          quantity: parseFloat(materialForm.quantity),
          unit_price: parseFloat(materialForm.unit_price),
        });
      } else {
        await createTicketMaterial(ticketId, {
          material_name: materialForm.material_name,
          quantity: parseFloat(materialForm.quantity),
          unit_price: parseFloat(materialForm.unit_price),
        });
      }
      resetMaterialForm();
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save material');
    } finally {
      setSubmitting(false);
    }
  };

  const handleManpowerSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canEdit) return;
    if (!manpowerForm.person_name || !manpowerForm.hours_worked || !manpowerForm.hourly_rate) {
      setError('Please fill in personnel name, hours worked, and hourly rate.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (editingManpowerId) {
        await updateTicketManpower(ticketId, editingManpowerId, {
          person_name: manpowerForm.person_name,
          hours_worked: parseFloat(manpowerForm.hours_worked),
          hourly_rate: parseFloat(manpowerForm.hourly_rate),
        });
      } else {
        await createTicketManpower(ticketId, {
          person_name: manpowerForm.person_name,
          hours_worked: parseFloat(manpowerForm.hours_worked),
          hourly_rate: parseFloat(manpowerForm.hourly_rate),
        });
      }
      resetManpowerForm();
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save manpower entry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleMaterialEdit = (entry: TicketMaterialEntry) => {
    setEditingMaterialId(entry.id);
    setMaterialForm({
      material_name: entry.material_name,
      quantity: entry.quantity,
      unit_price: entry.unit_price,
    });
  };

  const handleManpowerEdit = (entry: TicketManpowerEntry) => {
    setEditingManpowerId(entry.id);
    setManpowerForm({
      person_name: entry.person_name,
      hours_worked: entry.hours_worked,
      hourly_rate: entry.hourly_rate,
    });
  };

  const handleMaterialDelete = async (entry: TicketMaterialEntry) => {
    if (!canDelete) return;
    if (!window.confirm(`Delete material "${entry.material_name}"?`)) return;
    setSubmitting(true);
    setError(null);
    try {
      await deleteTicketMaterial(ticketId, entry.id);
      if (editingMaterialId === entry.id) {
        resetMaterialForm();
      }
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete material');
    } finally {
      setSubmitting(false);
    }
  };

  const handleManpowerDelete = async (entry: TicketManpowerEntry) => {
    if (!canDelete) return;
    if (!window.confirm(`Delete manpower entry for "${entry.person_name}"?`)) return;
    setSubmitting(true);
    setError(null);
    try {
      await deleteTicketManpower(ticketId, entry.id);
      if (editingManpowerId === entry.id) {
        resetManpowerForm();
      }
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete manpower entry');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-2">
        <h3 className="text-sm font-semibold text-slate-900">Materials & Manpower</h3>
      </div>
      <div className="space-y-6 p-4">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-800">Materials</h4>
            {canEdit && (
              <span className="text-xs text-slate-500">
                {editingMaterialId ? 'Editing existing material' : 'Add new material entries'}
              </span>
            )}
          </div>

          {materials.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">No materials recorded.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Material</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Quantity</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Unit Price</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {materials.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2 text-slate-800">{entry.material_name}</td>
                      <td className="px-3 py-2 text-slate-600">{entry.quantity}</td>
                      <td className="px-3 py-2 text-slate-600">{entry.unit_price}</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          {canEdit && (
                            <button
                              type="button"
                              onClick={() => handleMaterialEdit(entry)}
                              className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                            >
                              Edit
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              onClick={() => handleMaterialDelete(entry)}
                              className="rounded border border-rose-300 px-2 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50"
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

          {canEdit && (
            <form onSubmit={handleMaterialSubmit} className="mt-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-4">
              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-600">
                  Material Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={materialForm.material_name}
                  onChange={(event) => setMaterialForm({ ...materialForm, material_name: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="e.g. Replacement fan motor"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600">
                  Quantity <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={materialForm.quantity}
                  onChange={(event) => setMaterialForm({ ...materialForm, quantity: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600">
                  Unit Price <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={materialForm.unit_price}
                  onChange={(event) => setMaterialForm({ ...materialForm, unit_price: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
              <div className="flex items-end gap-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:opacity-60"
                >
                  {editingMaterialId ? (submitting ? 'Updating…' : 'Update') : submitting ? 'Saving…' : 'Add Material'}
                </button>
                {editingMaterialId && (
                  <button
                    type="button"
                    onClick={resetMaterialForm}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-800">Manpower</h4>
            {canEdit && (
              <span className="text-xs text-slate-500">
                {editingManpowerId ? 'Editing existing manpower entry' : 'Track hours spent on this ticket'}
              </span>
            )}
          </div>

          {manpower.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              No manpower entries recorded.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Person</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Hours</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Hourly Rate</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {manpower.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2 text-slate-800">{entry.person_name}</td>
                      <td className="px-3 py-2 text-slate-600">{entry.hours_worked}</td>
                      <td className="px-3 py-2 text-slate-600">{entry.hourly_rate}</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          {canEdit && (
                            <button
                              type="button"
                              onClick={() => handleManpowerEdit(entry)}
                              className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                            >
                              Edit
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              onClick={() => handleManpowerDelete(entry)}
                              className="rounded border border-rose-300 px-2 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50"
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

          {canEdit && (
            <form onSubmit={handleManpowerSubmit} className="mt-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600">
                  Person Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={manpowerForm.person_name}
                  onChange={(event) => setManpowerForm({ ...manpowerForm, person_name: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="Technician name"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600">
                  Hours Worked <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={manpowerForm.hours_worked}
                  onChange={(event) => setManpowerForm({ ...manpowerForm, hours_worked: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600">
                  Hourly Rate <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={manpowerForm.hourly_rate}
                  onChange={(event) => setManpowerForm({ ...manpowerForm, hourly_rate: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
              <div className="flex items-end gap-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:opacity-60"
                >
                  {editingManpowerId ? (submitting ? 'Updating…' : 'Update') : submitting ? 'Saving…' : 'Add Manpower'}
                </button>
                {editingManpowerId && (
                  <button
                    type="button"
                    onClick={resetManpowerForm}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          )}
        </section>
      </div>
    </div>
  );
};


