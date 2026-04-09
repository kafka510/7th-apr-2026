/**
 * PV Modules List Component
 * Displays and manages the library of PV module datasheets
 */
import React, { useState } from 'react';
import { usePVModules } from '../hooks/usePVModules';
import { PVModuleModal } from './PVModuleModal';
import { PVModuleImportModal } from './PVModuleImportModal';
import { DeleteConfirmModal } from './DeleteConfirmModal';
import { pvModuleApi } from '../api/pvModules';
import type { PVModuleDatasheet } from '../types/pvModules';
import { useTheme } from '../../../contexts/ThemeContext';

interface PVModulesListProps {
  onModuleChange: () => void;
}

export const PVModulesList: React.FC<PVModulesListProps> = ({ onModuleChange }) => {
  const { theme } = useTheme();
  const { modules, loading, error, createModule, updateModule, deleteModule, importModules, exportModules } = usePVModules();
  const [modalOpen, setModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<PVModuleDatasheet | null>(null);
  const [deletingModule, setDeletingModule] = useState<PVModuleDatasheet | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Theme-aware colors
  const bgColor = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textSecondary = theme === 'dark' ? '#cbd5e0' : '#4a5568';
  const textTertiary = theme === 'dark' ? '#94a3b8' : '#6b7280';
  const borderColor = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#e5e7eb';
  const borderHover = theme === 'dark' ? 'rgba(59, 130, 246, 0.8)' : '#3b82f6';
  const cardHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : '#f9fafb';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fef2f2';
  const errorText = theme === 'dark' ? '#fca5a5' : '#dc2626';

  const handleAddModule = () => {
    setEditingModule(null);
    setModalOpen(true);
  };

  const handleEditModule = async (module: PVModuleDatasheet) => {
    // Fetch full module details before editing
    // (list API only returns summary fields)
    try {
      const fullModuleData = await pvModuleApi.get(module.id);
      console.log('📥 Fetched full module data:', fullModuleData);
      setEditingModule(fullModuleData);
      setModalOpen(true);
    } catch (error) {
      window.alert(`Failed to load module details: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleSaveModule = async (moduleData: Partial<PVModuleDatasheet>) => {
    if (editingModule) {
      const success = await updateModule(editingModule.id, moduleData);
      if (success) onModuleChange();
      return success;
    } else {
      const success = await createModule(moduleData);
      if (success) onModuleChange();
      return success;
    }
  };

  const handleExport = async () => {
    await exportModules();
  };

  const handleImport = async (file: File, mode: 'create' | 'update' | 'both') => {
    const result = await importModules(file, mode);
    if (result) onModuleChange();
    return result;
  };

  const handleDownloadTemplate = async () => {
    await pvModuleApi.downloadTemplate();
  };

  const handleDeleteClick = (module: PVModuleDatasheet, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletingModule(module);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async (force: boolean) => {
    if (!deletingModule) return false;
    const success = await deleteModule(deletingModule.id, force);
    if (success) onModuleChange();
    return success;
  };

  const filteredModules = modules.filter((module) =>
    module.module_model.toLowerCase().includes(searchTerm.toLowerCase()) ||
    module.manufacturer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="pv-modules-list rounded p-4 shadow" style={{ backgroundColor: bgColor, borderColor: borderColor }}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-xl font-semibold" style={{ color: textColor }}>☀️ PV Module Library</h3>
        <div className="flex gap-2">
          <button 
            className="btn btn-primary"
            onClick={handleAddModule}
          >
            ➕ Add Module
          </button>
          <button 
            className="btn btn-outline-secondary"
            onClick={() => setImportModalOpen(true)}
          >
            📥 Import CSV
          </button>
          <button 
            className="btn btn-outline-secondary"
            onClick={handleExport}
          >
            📤 Export CSV
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          className="form-control"
          placeholder="Search by manufacturer or model..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            backgroundColor: inputBg,
            color: textColor,
            borderColor: borderColor
          }}
        />
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 rounded p-3" style={{ backgroundColor: errorBg, color: errorText }}>
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="py-8 text-center">
          <div style={{ color: textTertiary }}>Loading modules...</div>
        </div>
      )}

      {/* Modules Grid */}
      {!loading && !error && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredModules.map((module) => (
            <div
              key={module.id}
              className="group relative cursor-pointer rounded-lg border p-4 transition hover:shadow-md"
              style={{
                backgroundColor: bgColor,
                borderColor: borderColor
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = borderHover;
                e.currentTarget.style.backgroundColor = cardHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = borderColor;
                e.currentTarget.style.backgroundColor = bgColor;
              }}
              onClick={() => handleEditModule(module)}
            >
              <button
                onClick={(e) => handleDeleteClick(module, e)}
                className="absolute right-2 top-2 hidden rounded px-2 py-1 text-xs group-hover:block"
                style={{
                  backgroundColor: theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fee2e2',
                  color: theme === 'dark' ? '#fca5a5' : '#dc2626'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(127, 29, 29, 0.5)' : '#fecaca';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fee2e2';
                }}
              >
                🗑️ Delete
              </button>
              <h4 className="font-semibold" style={{ color: textColor }}>{module.module_model}</h4>
              <p className="text-sm" style={{ color: textSecondary }}>{module.manufacturer}</p>
              <div className="mt-2 text-sm" style={{ color: textTertiary }}>
                <div>{module.pmax_stc}Wp • {module.module_efficiency_stc}% eff</div>
                <div>{module.cells_per_module} cells • {module.technology}</div>
                {module.fill_factor && (
                  <div className="text-xs">FF: {module.fill_factor.toFixed(3)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredModules.length === 0 && (
        <div className="py-8 text-center" style={{ color: textTertiary }}>
          <p>No modules found{searchTerm ? ' matching your search' : ''}.</p>
          <p className="mt-2 text-sm">Click &quot;Add Module&quot; to create your first module datasheet.</p>
        </div>
      )}

      {/* Module Modal */}
      <PVModuleModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditingModule(null);
        }}
        onSave={handleSaveModule}
        editModule={editingModule}
        mode={editingModule ? 'edit' : 'create'}
      />

      {/* Import Modal */}
      <PVModuleImportModal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onImport={handleImport}
        onDownloadTemplate={handleDownloadTemplate}
        onAddManually={() => {
          setImportModalOpen(false);
          handleAddModule();
        }}
      />

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleDeleteConfirm}
        title="⚠️ Delete PV Module"
        message="Are you sure you want to delete this PV module datasheet?"
        itemName={deletingModule ? `${deletingModule.manufacturer} - ${deletingModule.module_model}` : ''}
        showForceOption={true}
        warningMessage="Devices using this module will have their configuration cleared."
      />
    </div>
  );
};

