/**
 * Modern TicketForm using React Hook Form + Zod + Radix UI
 * This is a migration from the original TicketForm.tsx
 * 
 * Features:
 * - React Hook Form for form state management
 * - Zod schema validation
 * - Radix UI components for better accessibility
 * - Toast notifications
 * - Preserves all existing cascading dropdown logic
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useTheme } from '../../../contexts/ThemeContext';
import { useFilterPersistence } from '../../../hooks/useFilterPersistence';
import { loadFilters } from '../../../utils/filterPersistence';
import {
  createTicket,
  fetchDeviceOptions,
  fetchDeviceTypes,
  fetchLocationOptions,
  fetchTicketDetail,
  fetchTicketFormOptions,
  fetchTicketListFilters,
  updateTicket,
} from '../api';
import type { BasicOption, DeviceOption, TicketFormData, TicketFormOptions } from '../types';
import { ticketFormSchema, type TicketFormSchemaType } from '../schemas/ticketFormSchema';
import { FormMultiSelect } from '../../../components/ui/form-multi-select';

type TicketFormProps = {
  mode?: 'create' | 'edit';
  ticketId?: string | null;
};

type TicketCreateFilterState = TicketFormSchemaType & {
  siteAssetId?: string;
  [key: string]: unknown;
};

export const TicketFormModern = ({ mode: initialMode, ticketId: propTicketId }: TicketFormProps) => {
  const { theme } = useTheme();
  
  // Theme colors (same as original)
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const sectionHeaderBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const labelColor = theme === 'dark' ? '#cbd5e1' : '#475569';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  // const inputPlaceholder = theme === 'dark' ? '#64748b' : '#94a3b8'; // unused with RHF styling
  // const inputFocusBorder = theme === 'dark' ? '#3b82f6' : '#0072ce'; // unused with RHF styling
  const inputErrorBorder = theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : '#f87171';
  const disabledBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const disabledText = theme === 'dark' ? '#64748b' : '#94a3b8';
  const disabledBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.6)' : 'rgba(203, 213, 225, 0.7)';
  const secondaryText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const errorText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  // const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fef2f2'; // unused with RHF styling
  // const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : '#fecaca'; // unused with RHF styling
  const cancelButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const cancelButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cancelButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const cancelButtonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#f8fafc';
  const submitButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.8)' : '#0072ce';
  const submitButtonHoverBg = theme === 'dark' ? 'rgba(37, 99, 235, 0.9)' : '#0056a3';
  const skeletonBg = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const actionBarBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const actionBarBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  
  // --- Helpers to read ticket id from DOM if not passed as prop
  const getTicketIdFromDOM = () => {
    if (propTicketId !== undefined) return propTicketId;
    const root = document.getElementById('react-root');
    return root?.dataset.ticketId ?? null;
  };

  const ticketId = getTicketIdFromDOM();
  const mode = initialMode || (ticketId ? 'edit' : 'create');
  const dashboardId = mode === 'create' ? 'ticket-create' : 'ticket-edit';

  // Track when we've attempted to hydrate from stored form state (create mode only)
  const [hasLoadedFromStorage, setHasLoadedFromStorage] = useState<boolean>(mode !== 'create');

  // --- React Hook Form setup
  const {
    register,
    handleSubmit: rhfHandleSubmit,
    formState: { errors: formErrors, isSubmitting },
    setValue,
    watch,
    reset,
  } = useForm<TicketFormSchemaType>({
    resolver: zodResolver(ticketFormSchema),
    defaultValues: {
      title: '',
      description: '',
      asset_code: '',
      location: '',
      device_type: '',
      device_id: '',
      sub_device_id: '',
      category: '',
      sub_category: '',
      loss_category: '',
      loss_value: undefined,
      priority: 'medium',
      assigned_to: '',
      watchers: [],
    },
  });

  // Watch form values for cascading logic
  const watchedValues = watch();
  const assetCode = watchedValues.asset_code;
  const location = watchedValues.location;
  const deviceId = watchedValues.device_id;

  // --- Core state (same as original)
  const [formOptions, setFormOptions] = useState<TicketFormOptions | null>(null);
  const [filterOptions, setFilterOptions] = useState<{
    siteOptions: Array<{ value: string; label: string; assetCode?: string | null; assetNumber?: string | null }>;
    assetNumberOptions: Array<{ value: string; label: string }>;
  } | null>(null);

  const [deviceTypes, setDeviceTypes] = useState<string[]>([]);
  const [devices, setDevices] = useState<DeviceOption[]>([]);
  const [subDevices, setSubDevices] = useState<DeviceOption[]>([]);
  const [locationOptions, setLocationOptions] = useState<BasicOption[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadingDeviceTypes, setLoadingDeviceTypes] = useState(false);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [loadingSubDevices, setLoadingSubDevices] = useState(false);
  const [loadingLocations, setLoadingLocations] = useState(false);

  // Combined site_asset id (value stored is `${assetCode}_${assetNumber}`)
  const [siteAssetId, setSiteAssetId] = useState<string>('');
  // Auto-calculated warranty status string
  const [warrantyStatus, setWarrantyStatus] = useState<string>('');

  // --- Build combined Site_Asset ID options (memoized) - same as original
  const siteAssetIdOptions = useMemo(() => {
    if (!filterOptions?.siteOptions || !filterOptions?.assetNumberOptions) return [];

    const out: Array<{ value: string; label: string; assetCode: string; assetNumber: string }> = [];
    const { siteOptions: sites, assetNumberOptions: assets } = filterOptions;

    // Strategy 1: site records that already include assetNumber
    sites.forEach((site) => {
      if (site.assetNumber) {
        const assetNumber = String(site.assetNumber).trim();
        const match = assets.find((a) => String(a.value || '').trim() === assetNumber || String(a.label || '').trim() === assetNumber);
        const assetLabel = match?.label || assetNumber;
        out.push({
          value: `${site.value}_${assetNumber}`,
          label: `${site.label}_${assetLabel}`,
          assetCode: site.value,
          assetNumber,
        });
      }
    });

    // Strategy 2: cross-match sites <> assets
    sites.forEach((site) => {
      assets.forEach((asset) => {
        const siteValue = String(site.value).trim();
        const siteLabel = String(site.label).trim();
        const siteAssetCode = site.assetCode ? String(site.assetCode).trim() : '';
        const assetValue = String(asset.value).trim();
        const assetLabel = String(asset.label).trim();

        const already = out.some((o) => o.assetCode === site.value && o.assetNumber === asset.value);
        if (already) return;

        const matched =
          assetValue === siteValue ||
          assetLabel === siteValue ||
          assetValue === siteLabel ||
          assetLabel === siteLabel ||
          assetValue === siteAssetCode ||
          assetLabel === siteAssetCode;

        if (matched) {
          out.push({
            value: `${site.value}_${asset.value}`,
            label: `${site.label}_${asset.label}`,
            assetCode: site.value,
            assetNumber: asset.value,
          });
        }
      });
    });

    return out.sort((a, b) => a.label.localeCompare(b.label));
  }, [filterOptions]);

  // --- Load initial form options + list filters
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [formOpts, filterOpts] = await Promise.all([fetchTicketFormOptions(), fetchTicketListFilters()]);
        if (!mounted) return;
        setFormOptions(formOpts);

        const siteOptions = (filterOpts.siteOptions || []).map((site) => ({
          value: site.value,
          label: site.label,
          assetCode: site.assetCode || null,
          assetNumber: site.assetNumber || null,
        }));
        const assetNumberOptions = filterOpts.assetNumberOptions || [];
        setFilterOptions({ siteOptions, assetNumberOptions });
      } catch (err) {
        console.error('Failed to load ticket form options or filters', err);
        toast.error('Failed to load form options');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  // --- Handler: change combined Site_Asset ID (same logic as original)
  const handleSiteAssetIdChange = useCallback(
    async (value: string) => {
      setSiteAssetId(value);

      if (!value) {
        setValue('asset_code', '');
        setValue('location', '');
        setValue('device_type', '');
        setValue('device_id', '');
        setValue('sub_device_id', '');
        setDeviceTypes([]);
        setDevices([]);
        setSubDevices([]);
        setLocationOptions([]);
        return;
      }

      const selected = siteAssetIdOptions.find((o) => o.value === value);
      if (!selected) {
        setValue('asset_code', '');
        setValue('location', '');
        setValue('device_type', '');
        setValue('device_id', '');
        setValue('sub_device_id', '');
        return;
      }

      if (selected.assetCode !== assetCode) {
        setValue('asset_code', selected.assetCode);
        setValue('location', '');
        setValue('device_type', '');
        setValue('device_id', '');
        setValue('sub_device_id', '');
        setDeviceTypes([]);
        setDevices([]);
        setSubDevices([]);
        setLocationOptions([]);

        if (selected.assetCode) {
          setLoadingLocations(true);
          setLoadingDeviceTypes(true);
          try {
            const [locations, types] = await Promise.all([
              fetchLocationOptions(selected.assetCode),
              fetchDeviceTypes(selected.assetCode),
            ]);
            setLocationOptions(locations || []);
            setDeviceTypes((types || []).map((t) => t.toUpperCase()));
          } catch (err) {
            console.error('Failed to load locations or device types', err);
            setLocationOptions([]);
            setDeviceTypes([]);
            toast.error('Failed to load locations or device types');
          } finally {
            setLoadingLocations(false);
            setLoadingDeviceTypes(false);
          }
        }
      }
    },
    [assetCode, siteAssetIdOptions, setValue],
  );

  // Hydrate create form from persisted state (for Playwright export)
  useEffect(() => {
    if (mode !== 'create') {
      return;
    }
    if (hasLoadedFromStorage) {
      return;
    }
    if (loading) {
      return;
    }
    if (siteAssetIdOptions.length === 0) {
      return;
    }

    const stored = loadFilters<TicketCreateFilterState>(dashboardId);
    if (stored && typeof stored === 'object' && Object.keys(stored).length > 0) {
      const { siteAssetId: storedSiteAssetId, ...storedValues } = stored;

      // Apply stored form values
      reset({
        title: storedValues.title ?? '',
        description: storedValues.description ?? '',
        asset_code: storedValues.asset_code ?? '',
        location: storedValues.location ?? '',
        device_type: storedValues.device_type ?? '',
        device_id: storedValues.device_id ?? '',
        sub_device_id: storedValues.sub_device_id ?? '',
        category: storedValues.category ?? '',
        sub_category: storedValues.sub_category ?? '',
        loss_category: storedValues.loss_category ?? '',
        loss_value: storedValues.loss_value as number | undefined,
        priority: (storedValues.priority as string) ?? 'medium',
        assigned_to: storedValues.assigned_to ?? '',
        watchers: (storedValues.watchers as string[] | undefined) ?? [],
      });

      // Restore combined Site_Asset selection (and cascading data)
      if (storedSiteAssetId && typeof storedSiteAssetId === 'string') {
        setSiteAssetId(storedSiteAssetId);
        // Trigger existing cascading logic to reload locations/devices
        void handleSiteAssetIdChange(storedSiteAssetId);
      }
    }

    setHasLoadedFromStorage(true);
  }, [
    mode,
    hasLoadedFromStorage,
    loading,
    dashboardId,
    reset,
    handleSiteAssetIdChange,
    siteAssetIdOptions,
  ]);

  // --- Edit mode: load ticket details
  useEffect(() => {
    if (mode !== 'edit' || !ticketId) return;
    let mounted = true;

    const loadTicket = async () => {
      try {
        const ticket = await fetchTicketDetail(ticketId);
        if (!mounted) return;

        const metadata = ticket.metadata as Record<string, unknown> | undefined;
        const deviceInfo = (metadata?.device_info || {}) as { device_id?: string; device_type?: string } | undefined;

        const categoryId =
          formOptions?.categories?.find((c) => c.label === ticket.category)?.value ||
          ticket.category ||
          '';
        const lossCategoryId =
          formOptions?.lossCategories?.find((l) => l.label === ticket.loss_category)?.value ||
          ticket.loss_category ||
          '';
        const subCategoryId =
          ticket.sub_category?.id?.toString() ||
          formOptions?.subCategories?.find((s) => s.label === (metadata?.sub_category as string))?.value ||
          '';

        reset({
          title: ticket.title,
          description: ticket.description,
          asset_code: ticket.asset_code || '',
          location: (metadata?.location as string) || '',
          device_type: deviceInfo?.device_type ? deviceInfo.device_type.toUpperCase() : '',
          device_id: deviceInfo?.device_id || '',
          sub_device_id: (metadata?.sub_device_id as string) || '',
          category: categoryId,
          sub_category: subCategoryId,
          loss_category: lossCategoryId,
          loss_value: undefined,
          priority: ticket.priority,
          assigned_to: ticket.assigned_to?.id?.toString() || '',
          watchers: (ticket.watchers || []).map((w) => w?.id?.toString() || '').filter(Boolean),
        });

        // If asset_code exists, load dependent lists
        if (ticket.asset_code) {
          setLoadingLocations(true);
          try {
            const locations = await fetchLocationOptions(ticket.asset_code);
            if (mounted) setLocationOptions(locations || []);
          } catch (err) {
            console.error('Failed to load locations for edit', err);
            if (mounted) setLocationOptions([]);
          } finally {
            if (mounted) setLoadingLocations(false);
          }

          try {
            const types = await fetchDeviceTypes(ticket.asset_code);
            if (mounted) setDeviceTypes((types || []).map((t) => t.toUpperCase()));
          } catch (err) {
            console.error('Failed to load device types for edit', err);
            if (mounted) setDeviceTypes([]);
          }

          if (deviceInfo?.device_type) {
            setLoadingDevices(true);
            try {
              const loc = (metadata?.location as string) || '';
              const devs = await fetchDeviceOptions(ticket.asset_code, deviceInfo.device_type.toLowerCase(), undefined, loc);
              if (mounted) setDevices(devs || []);
            } catch (err) {
              console.error('Failed to load devices for edit', err);
              if (mounted) {
                setDevices([]);
                toast.error('Failed to load devices');
              }
            } finally {
              if (mounted) setLoadingDevices(false);
            }

            if (deviceInfo?.device_id) {
              setLoadingSubDevices(true);
              try {
                const loc = (metadata?.location as string) || '';
                const subs = await fetchDeviceOptions(ticket.asset_code, undefined, deviceInfo.device_id, loc);
                if (mounted) setSubDevices(subs || []);
              } catch (err) {
                console.error('Failed to load sub-devices for edit', err);
                if (mounted) setSubDevices([]);
              } finally {
                if (mounted) setLoadingSubDevices(false);
              }
            }
          }
        }
      } catch (err) {
        console.error('Failed to fetch ticket detail', err);
        toast.error('Failed to load ticket');
      }
    };

    loadTicket();
    return () => {
      mounted = false;
    };
  }, [mode, ticketId, formOptions, reset]);

  // --- When in edit mode and siteAssetId isn't set but we have asset_code, derive it
  useEffect(() => {
    if (mode !== 'edit' || !assetCode || siteAssetIdOptions.length === 0 || siteAssetId) return;
    const match = siteAssetIdOptions.find((opt) => opt.assetCode === assetCode);
    if (match) {
      setSiteAssetId(match.value);
      (async () => {
        setLoadingLocations(true);
        try {
          const locations = await fetchLocationOptions(assetCode);
          setLocationOptions(locations || []);
        } catch (err) {
          console.error('Failed to load locations in edit post-process', err);
          setLocationOptions([]);
        } finally {
          setLoadingLocations(false);
        }
      })();
    }
  }, [mode, assetCode, siteAssetIdOptions, siteAssetId]);

  // --- Sub-category options derived from selected category
  const subCategoryOptions = useMemo(() => {
    if (!formOptions?.subCategories || !watchedValues.category) return [];
    return formOptions.subCategories
      .filter((s) => s.category === watchedValues.category)
      .map((s) => ({ value: s.value, label: s.label }));
  }, [formOptions?.subCategories, watchedValues.category]);

  // --- Handle category change (reset subcategory)
  const handleCategoryChange = useCallback(
    (categoryValue: string) => {
      setValue('category', categoryValue);
      setValue('sub_category', '');
    },
    [setValue],
  );

  // --- Handle device type change
  const handleDeviceTypeChange = useCallback(
    async (deviceTypeValue: string) => {
      const isChanging = watchedValues.device_type !== deviceTypeValue;
      setValue('device_type', deviceTypeValue);
      setValue('device_id', isChanging ? '' : watchedValues.device_id);
      setValue('sub_device_id', isChanging ? '' : watchedValues.sub_device_id);

      if (isChanging) {
        setDevices([]);
        setSubDevices([]);
        setWarrantyStatus('');
      }

      if (deviceTypeValue && assetCode) {
        setLoadingDevices(true);
        try {
          const devs = await fetchDeviceOptions(assetCode, deviceTypeValue.toLowerCase(), undefined, location);
          setDevices(devs || []);
        } catch (err) {
          console.error('Failed to load devices when device type changed', err);
          setDevices([]);
          toast.error('Failed to load devices');
        } finally {
          setLoadingDevices(false);
        }
      } else {
        setLoadingDevices(false);
      }
    },
    [assetCode, location, setValue, watchedValues.device_id, watchedValues.device_type, watchedValues.sub_device_id],
  );

  // --- When location changes, filter device types and reload devices
  useEffect(() => {
    if (!assetCode) return;
    let mounted = true;

    const load = async () => {
      if (location) {
        setLoadingDeviceTypes(true);
        try {
          const devs = await fetchDeviceOptions(assetCode, undefined, undefined, location);
          if (!mounted) return;
          const locationDeviceTypes = Array.from(
            new Set((devs || []).map((d) => d.device_type).filter((t): t is string => Boolean(t)))
          ).map((t) => t.toUpperCase());

          setDeviceTypes(locationDeviceTypes);

          const currentDeviceType = watchedValues.device_type;
          if (currentDeviceType && !locationDeviceTypes.includes(currentDeviceType.toUpperCase())) {
            setValue('device_type', '');
            setValue('device_id', '');
            setValue('sub_device_id', '');
          }
        } catch (err) {
          console.error('Failed to filter device types by location', err);
        } finally {
          if (mounted) setLoadingDeviceTypes(false);
        }
      } else {
        setLoadingDeviceTypes(true);
        try {
          const types = await fetchDeviceTypes(assetCode);
          if (mounted) setDeviceTypes((types || []).map((t) => t.toUpperCase()));
        } catch (err) {
          console.error('Failed to load device types', err);
          if (mounted) setDeviceTypes([]);
        } finally {
          if (mounted) setLoadingDeviceTypes(false);
        }
      }

      if (watchedValues.device_type) {
        setLoadingDevices(true);
        try {
          const devs = await fetchDeviceOptions(assetCode, watchedValues.device_type?.toLowerCase(), undefined, location);
          if (!mounted) return;
          setDevices(devs || []);
          const currentDeviceId = watchedValues.device_id;
          if (currentDeviceId && !devs.some((d) => d.value === currentDeviceId)) {
            setValue('device_id', '');
            setValue('sub_device_id', '');
          }
        } catch (err) {
          console.error('Failed to reload devices on location change', err);
        } finally {
          if (mounted) setLoadingDevices(false);
        }
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [assetCode, location, setValue, watchedValues.device_type]);

  // --- Warranty calculation when device_id changes
  useEffect(() => {
    if (!deviceId || devices.length === 0) {
      setWarrantyStatus('');
      return;
    }
    const sel = devices.find((d) => d.value === deviceId);
    if (!sel) {
      setWarrantyStatus('');
      return;
    }
    const expiry = sel.warranty_expire_date;
    if (!expiry) {
      setWarrantyStatus('Data Not Available');
      return;
    }
    const expDate = new Date(expiry);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    expDate.setHours(0, 0, 0, 0);
    setWarrantyStatus(expDate >= today ? 'Yes' : 'No');
  }, [deviceId, devices]);

  // --- Load sub-devices when device changes
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      if (!assetCode || !deviceId) {
        setSubDevices([]);
        setValue('sub_device_id', '');
        return;
      }
      setLoadingSubDevices(true);
      try {
        const subs = await fetchDeviceOptions(assetCode, undefined, deviceId, location);
        if (!mounted) return;
        setSubDevices(subs || []);
        const currentSubDeviceId = watchedValues.sub_device_id;
        if (currentSubDeviceId && !subs.some((d) => d.value === currentSubDeviceId)) {
          setValue('sub_device_id', '');
        }
      } catch (err) {
        console.error('Failed to load sub-devices', err);
        if (mounted) setSubDevices([]);
      } finally {
        if (mounted) setLoadingSubDevices(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [assetCode, deviceId, location, setValue]);

  // --- Submit handler (create/update)
  const onSubmit = async (data: TicketFormSchemaType): Promise<void> => {
    try {
      const payload: TicketFormData = {
        ...data,
        device_type: data.device_type ? data.device_type.toLowerCase() : undefined,
        device_id: data.device_id || undefined,
        sub_device_id: data.sub_device_id || undefined,
        sub_category: data.sub_category || undefined,
        loss_category: data.loss_category || undefined,
        loss_value: data.loss_value === '' ? undefined : data.loss_value,
        assigned_to: data.assigned_to || undefined,
        watchers: data.watchers.filter(Boolean),
      };

      if (mode === 'create') {
        const result = await createTicket(payload);
        toast.success('Ticket created');
        window.location.href = `/tickets/${result.id}/`;
      } else if (ticketId) {
        await updateTicket(ticketId, payload);
        toast.success('Ticket updated');
        window.location.href = `/tickets/${ticketId}/`;
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save ticket';
      toast.error(message);
    }
  };

  // Persist current form state (for create/edit ticket pages) for Playwright export
  const persistenceState: TicketCreateFilterState = {
    ...watchedValues,
    siteAssetId,
  };
  useFilterPersistence<TicketCreateFilterState>(dashboardId, persistenceState);

  // Signal when Ticket Create/Edit page is ready for export/download
  useEffect(() => {
    // For create mode, wait until we've attempted to hydrate from storage
    if (loading) {
      document.body.removeAttribute('data-filters-ready');
      return;
    }

    if (mode === 'create' && !hasLoadedFromStorage) {
      return;
    }

    document.body.setAttribute('data-filters-ready', 'true');
    window.dispatchEvent(
      new CustomEvent('dashboard-filters-ready', { detail: { dashboardId } }),
    );

    return () => {
      document.body.removeAttribute('data-filters-ready');
    };
  }, [loading, mode, hasLoadedFromStorage, dashboardId]);

  // --- Loading skeleton
  if (loading) {
    return (
      <div 
        className="min-h-screen p-6"
        style={{
          background: bgGradient,
          color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
          transition: 'background 0.3s ease, color 0.3s ease',
        }}
      >
        <div className="mx-auto max-w-4xl">
          <div className="animate-pulse space-y-4">
            <div 
              className="h-8 w-64 rounded"
              style={{ backgroundColor: skeletonBg }}
            />
            <div className="grid grid-cols-1 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div 
                  key={i} 
                  className="h-14 rounded"
                  style={{ backgroundColor: skeletonBg }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="flex min-h-screen flex-col"
      style={{
        background: bgGradient,
        color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
        transition: 'background 0.3s ease, color 0.3s ease',
      }}
    >
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto w-full max-w-6xl">
          {/* Page Header */}
          <div className="mb-6">
            <h1 
              className="text-3xl font-bold"
              style={{ color: theme === 'dark' ? '#e2e8f0' : '#0f172a' }}
            >
              {mode === 'create' ? 'Create New Ticket' : 'Edit Ticket'}
            </h1>
          </div>

          <form onSubmit={rhfHandleSubmit(onSubmit)} className="flex flex-col gap-4">
            {/* Two-column section */}
            <div className="grid gap-4 md:grid-cols-2">
              {/* Left: Site & Device */}
              <section 
                className="rounded-xl border p-4 shadow-xl"
                style={{
                  borderColor: containerBorder,
                  background: containerBg,
                  boxShadow: containerShadow,
                }}
              >
                <div 
                  className="mb-3 flex items-center gap-2 border-b px-1 pb-2.5"
                  style={{
                    borderColor: sectionHeaderBorder,
                    background: theme === 'dark' 
                      ? 'linear-gradient(to right, rgba(14,165,233,0.15), rgba(56,189,248,0.1))'
                      : 'linear-gradient(to right, rgba(14,165,233,0.08), rgba(56,189,248,0.05))',
                  }}
                >
                  <span className="text-base">📍</span>
                  <h3 
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: theme === 'dark' ? '#38bdf8' : '#0072ce' }}
                  >
                    Site & Device Selection
                  </h3>
                </div>

                <div className="flex flex-col gap-3">
                  {/* Site_Asset ID */}
                  <FormMultiSelect
                    label="Site_Asset ID"
                    options={siteAssetIdOptions.map((o) => ({ value: o.value, label: o.label }))}
                    selected={siteAssetId ? [siteAssetId] : []}
                    onChange={(vals: string[]) => handleSiteAssetIdChange(vals[0] || '')}
                    placeholder={siteAssetIdOptions.length ? 'Select Site_Asset ID (e.g., Site_AssetNumber)' : 'Loading Site_Asset IDs...'}
                    disabled={siteAssetIdOptions.length === 0}
                    required
                    error={formErrors.asset_code?.message}
                    singleSelect
                  />
                  {siteAssetIdOptions.length > 0 && (
                    <p 
                      className="text-xs"
                      style={{ color: secondaryText }}
                    >
                      Format: Site Name_Asset Number
                    </p>
                  )}

                  {/* Location */}
                  <FormMultiSelect
                    label="Location"
                    options={locationOptions}
                    selected={watchedValues.location ? [watchedValues.location] : []}
                    onChange={(vals: string[]) => setValue('location', vals[0] || '')}
                    placeholder={!assetCode ? 'Select a site first' : loadingLocations ? 'Loading locations...' : locationOptions.length === 0 ? 'No locations available' : 'Select Location'}
                    disabled={!assetCode || loadingLocations}
                    error={formErrors.location?.message}
                    singleSelect
                  />

                  {/* Device Type */}
                  <FormMultiSelect
                    label="Device Type"
                    options={deviceTypes.map((t) => ({ value: t, label: t }))}
                    selected={watchedValues.device_type ? [watchedValues.device_type] : []}
                    onChange={(vals: string[]) => handleDeviceTypeChange(vals[0] || '')}
                    placeholder={!assetCode ? 'Select a site first' : loadingDeviceTypes ? 'Loading device types...' : deviceTypes.length === 0 ? 'No device types available' : 'Select Device Type'}
                    disabled={!assetCode || loadingDeviceTypes}
                    required
                    error={formErrors.device_type?.message}
                    singleSelect
                  />

                  {/* Device Name */}
                  <FormMultiSelect
                    label="Device Name"
                    options={devices}
                    selected={watchedValues.device_id ? [watchedValues.device_id] : []}
                    onChange={(vals: string[]) => setValue('device_id', vals[0] || '')}
                    placeholder={!assetCode ? 'Select a site first' : !watchedValues.device_type ? 'Select device type first' : loadingDevices ? 'Loading devices...' : devices.length === 0 ? 'No devices available' : 'Select Device'}
                    disabled={!assetCode || !watchedValues.device_type || loadingDevices}
                    required
                    error={formErrors.device_id?.message}
                    singleSelect
                  />

                  {/* Sub Device */}
                  <FormMultiSelect
                    label="Sub Device"
                    options={subDevices}
                    selected={watchedValues.sub_device_id ? [watchedValues.sub_device_id] : []}
                    onChange={(vals: string[]) => setValue('sub_device_id', vals[0] || '')}
                    placeholder={!watchedValues.device_id ? 'Select device first' : loadingSubDevices ? 'Loading sub-devices...' : subDevices.length === 0 ? 'No sub-devices available' : 'Select Sub Device'}
                    disabled={!watchedValues.device_id || loadingSubDevices}
                    singleSelect
                  />

                  {/* Warranty Status */}
                  <div>
                    <label 
                      className="block text-xs font-semibold"
                      style={{ color: labelColor }}
                    >
                      Warranty Status
                    </label>
                    <input
                      readOnly
                      disabled
                      value={warrantyStatus || 'Select a device to see warranty status'}
                      className="mt-1 w-full cursor-not-allowed rounded border px-2 py-1.5 text-sm"
                      style={{
                        borderColor: disabledBorder,
                        backgroundColor: disabledBg,
                        color: disabledText,
                      }}
                    />
                  </div>
                </div>
              </section>

              {/* Right: Basic Info */}
              <section 
                className="rounded-xl border p-4 shadow-xl"
                style={{
                  borderColor: containerBorder,
                  background: containerBg,
                  boxShadow: containerShadow,
                }}
              >
                <div 
                  className="mb-3 flex items-center gap-2 border-b px-1 pb-2.5"
                  style={{
                    borderColor: sectionHeaderBorder,
                    background: theme === 'dark' 
                      ? 'linear-gradient(to right, rgba(14,165,233,0.15), rgba(56,189,248,0.1))'
                      : 'linear-gradient(to right, rgba(14,165,233,0.08), rgba(56,189,248,0.05))',
                  }}
                >
                  <span className="text-base">ℹ️</span>
                  <h3 
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: theme === 'dark' ? '#38bdf8' : '#0072ce' }}
                  >
                    Basic Information
                  </h3>
                </div>

                <div className="flex flex-col gap-3">
                  {/* Title */}
                  <div>
                    <label 
                      htmlFor="title" 
                      className="block text-xs font-semibold"
                      style={{ color: labelColor }}
                    >
                      Title <span style={{ color: errorText }}>*</span>
                    </label>
                    <input
                      id="title"
                      {...register('title')}
                      placeholder="Enter ticket title"
                      className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
                      style={{
                        borderColor: formErrors.title ? inputErrorBorder : inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                        boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
                      }}
                    />
                    {formErrors.title && (
                      <p 
                        className="mt-1 text-xs"
                        style={{ color: errorText }}
                      >
                        {formErrors.title.message}
                      </p>
                    )}
                  </div>

                  {/* Description */}
                  <div>
                    <label 
                      htmlFor="description" 
                      className="block text-xs font-semibold"
                      style={{ color: labelColor }}
                    >
                      Description <span style={{ color: errorText }}>*</span>
                    </label>
                    <textarea
                      id="description"
                      {...register('description')}
                      rows={3}
                      placeholder="Provide detailed description of the issue..."
                      className="mt-1 w-full resize-none rounded border px-2 py-1.5 text-sm"
                      style={{
                        borderColor: formErrors.description ? inputErrorBorder : inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                        boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
                      }}
                    />
                    {formErrors.description && (
                      <p 
                        className="mt-1 text-xs"
                        style={{ color: errorText }}
                      >
                        {formErrors.description.message}
                      </p>
                    )}
                  </div>

                  {/* Category */}
                  {formOptions?.categories ? (
                    <FormMultiSelect
                      label="Category"
                      options={formOptions.categories}
                      selected={watchedValues.category ? [watchedValues.category] : []}
                      onChange={(vals: string[]) => handleCategoryChange(vals[0] || '')}
                      placeholder="Select Category"
                      required
                      error={formErrors.category?.message}
                      singleSelect
                    />
                  ) : (
                    <div>
                      <label 
                        className="block text-xs font-semibold"
                        style={{ color: labelColor }}
                      >
                        Category
                      </label>
                      <div 
                        className="mt-1 text-xs"
                        style={{ color: secondaryText }}
                      >
                        Loading categories...
                      </div>
                    </div>
                  )}

                  {/* Sub-Category */}
                  <FormMultiSelect
                    label="Sub-Category"
                    options={subCategoryOptions}
                    selected={watchedValues.sub_category ? [watchedValues.sub_category] : []}
                    onChange={(vals: string[]) => setValue('sub_category', vals[0] || '')}
                    placeholder={watchedValues.category ? (subCategoryOptions.length ? 'Select Sub-Category' : 'No sub-categories') : 'Select Category first'}
                    disabled={!watchedValues.category || subCategoryOptions.length === 0}
                    singleSelect
                  />

                  {/* Priority */}
                  {formOptions?.priorities ? (
                    <FormMultiSelect
                      label="Priority"
                      options={formOptions.priorities}
                      selected={watchedValues.priority ? [watchedValues.priority] : []}
                      onChange={(vals: string[]) => setValue('priority', vals[0] || 'medium')}
                      placeholder="Select Priority"
                      required
                      singleSelect
                    />
                  ) : (
                    <div>
                      <label 
                        className="block text-xs font-semibold"
                        style={{ color: labelColor }}
                      >
                        Priority
                      </label>
                      <div 
                        className="mt-1 text-xs"
                        style={{ color: secondaryText }}
                      >
                        Loading priorities...
                      </div>
                    </div>
                  )}

                  {/* Loss Category */}
                  {formOptions?.lossCategories ? (
                    <FormMultiSelect
                      label="Loss Category"
                      options={formOptions.lossCategories}
                      selected={watchedValues.loss_category ? [watchedValues.loss_category] : []}
                      onChange={(vals: string[]) => setValue('loss_category', vals[0] || '')}
                      placeholder="Select Loss Category"
                      singleSelect
                    />
                  ) : (
                    <div>
                      <label 
                        className="block text-xs font-semibold"
                        style={{ color: labelColor }}
                      >
                        Loss Category
                      </label>
                      <div 
                        className="mt-1 text-xs"
                        style={{ color: secondaryText }}
                      >
                        Loading loss categories...
                      </div>
                    </div>
                  )}

                  {/* Loss Value */}
                  <div>
                    <label 
                      htmlFor="loss_value" 
                      className="block text-xs font-semibold"
                      style={{ color: labelColor }}
                    >
                      Loss Value <span className="text-xs" style={{ color: secondaryText }}>(Optional)</span>
                    </label>
                    <input
                      id="loss_value"
                      type="number"
                      step="0.01"
                      min="0"
                      value={watchedValues.loss_value ?? ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        setValue('loss_value', val === '' ? undefined : parseFloat(val));
                      }}
                      placeholder="0.00"
                      className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
                      style={{
                        borderColor: formErrors.loss_value ? inputErrorBorder : inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                        boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
                      }}
                    />
                    {formErrors.loss_value && (
                      <p 
                        className="mt-1 text-xs"
                        style={{ color: errorText }}
                      >
                        {formErrors.loss_value.message as string}
                      </p>
                    )}
                  </div>

                  {/* Assign To */}
                  {formOptions?.users ? (
                    <FormMultiSelect
                      label="Assign To"
                      options={formOptions.users}
                      selected={watchedValues.assigned_to ? [watchedValues.assigned_to] : []}
                      onChange={(vals: string[]) => setValue('assigned_to', vals[0] || '')}
                      placeholder="Select User"
                      singleSelect
                    />
                  ) : (
                    <div>
                      <label 
                        className="block text-xs font-semibold"
                        style={{ color: labelColor }}
                      >
                        Assign To
                      </label>
                      <div 
                        className="mt-1 text-xs"
                        style={{ color: secondaryText }}
                      >
                        Loading users...
                      </div>
                    </div>
                  )}

                  {/* Watchers */}
                  <div>
                    {formOptions?.users ? (
                      <FormMultiSelect
                        label="Watchers / Collaborators"
                        options={formOptions.users}
                        selected={watchedValues.watchers || []}
                        onChange={(vals: string[]) => setValue('watchers', vals)}
                        placeholder="Select watchers"
                      />
                    ) : (
                      <>
                        <label 
                          className="block text-xs font-semibold"
                          style={{ color: labelColor }}
                        >
                          Watchers / Collaborators
                        </label>
                        <div 
                          className="mt-1 text-xs"
                          style={{ color: secondaryText }}
                        >
                          Loading users...
                        </div>
                      </>
                    )}
                    <p 
                      className="mt-1 text-xs"
                      style={{ color: secondaryText }}
                    >
                      Search and select multiple users
                    </p>
                  </div>
                </div>
              </section>
            </div>

            {/* Actions */}
            <div 
              className="flex items-center justify-end gap-3 rounded-xl border p-4 shadow-lg"
              style={{
                backgroundColor: actionBarBg,
                borderColor: actionBarBorder,
              }}
            >
              <button
                type="button"
                onClick={() => {
                  if (mode === 'edit' && ticketId) window.location.href = `/tickets/${ticketId}/`;
                  else window.location.href = '/tickets/';
                }}
                className="rounded-lg border px-4 py-2 text-sm font-semibold transition-all hover:scale-105"
                style={{
                  borderColor: cancelButtonBorder,
                  backgroundColor: cancelButtonBg,
                  color: cancelButtonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = cancelButtonHoverBg;
                  e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(56, 189, 248, 0.5)' : 'rgba(14, 165, 233, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = cancelButtonBg;
                  e.currentTarget.style.borderColor = cancelButtonBorder;
                }}
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
                style={{
                  backgroundColor: submitButtonBg,
                }}
                onMouseEnter={(e) => {
                  if (!isSubmitting) {
                    e.currentTarget.style.backgroundColor = submitButtonHoverBg;
                    e.currentTarget.style.boxShadow = theme === 'dark' 
                      ? '0 4px 12px rgba(56, 189, 248, 0.4)'
                      : '0 4px 12px rgba(0, 114, 206, 0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSubmitting) {
                    e.currentTarget.style.backgroundColor = submitButtonBg;
                    e.currentTarget.style.boxShadow = '';
                  }
                }}
              >
                {isSubmitting ? '⏳ Saving...' : mode === 'create' ? '✓ Create Ticket' : '✓ Update Ticket'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default TicketFormModern;

