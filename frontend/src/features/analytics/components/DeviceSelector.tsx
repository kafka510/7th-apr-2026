/**
 * Device Selector Component with grouping by device type
 */
 
import { useState, useMemo } from 'react';
import type { Device } from '../types';

interface DeviceSelectorProps {
  devices: Device[];
  selectedDeviceIds: string[];
  onDeviceSelectionChange: (deviceIds: string[]) => void;
  loading?: boolean;
}

export function DeviceSelector({
  devices,
  selectedDeviceIds,
  onDeviceSelectionChange,
  loading = false,
}: DeviceSelectorProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Group devices by device type
  const devicesByType = useMemo(() => {
    const grouped: Record<string, Device[]> = {};
    devices.forEach((device) => {
      if (!grouped[device.device_type]) {
        grouped[device.device_type] = [];
      }
      grouped[device.device_type].push(device);
    });
    return grouped;
  }, [devices]);

  const toggleGroup = (deviceType: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(deviceType)) {
        next.delete(deviceType);
      } else {
        next.add(deviceType);
      }
      return next;
    });
  };

  const handleDeviceToggle = (deviceId: string, checked: boolean) => {
    if (checked) {
      onDeviceSelectionChange([...selectedDeviceIds, deviceId]);
    } else {
      onDeviceSelectionChange(selectedDeviceIds.filter((id) => id !== deviceId));
    }
  };

  const selectAllDevices = () => {
    // Expand all groups first
    setExpandedGroups(new Set(Object.keys(devicesByType)));
    onDeviceSelectionChange(devices.map((d) => d.device_id));
  };

  const clearAllDevices = () => {
    onDeviceSelectionChange([]);
  };

  if (loading) {
    return (
      <div className="mb-4">
        <label className="mb-2 block text-sm font-bold text-slate-900">Select Devices</label>
        <div className="font-medium text-slate-700">Loading devices...</div>
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <div className="mb-4">
        <label className="mb-2 block text-sm font-bold text-slate-900">Select Devices</label>
        <div className="font-medium text-slate-700">No devices found for this site</div>
      </div>
    );
  }

  return (
    <div className="mb-4">
      <div className="mb-2 flex items-center justify-between">
        <label className="block text-sm font-semibold text-slate-700">Select Devices</label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={selectAllDevices}
            className="rounded border border-blue-500 bg-white px-3 py-1 text-xs text-blue-500 hover:bg-blue-50"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={clearAllDevices}
            className="rounded border border-slate-400 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
          >
            Clear All
          </button>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto rounded border-2 border-slate-200 bg-slate-50 p-4">
        {Object.keys(devicesByType)
          .sort()
          .map((deviceType) => {
            const isExpanded = expandedGroups.has(deviceType);
            const groupDevices = devicesByType[deviceType];

            return (
              <div key={deviceType} className="mb-2 rounded border border-slate-300 bg-white">
                {/* Group Header */}
                <div
                  className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 p-3 transition-colors hover:bg-slate-100"
                  onClick={() => toggleGroup(deviceType)}
                >
                  <div className="flex items-center">
                    <h6 className="m-0 text-sm font-bold text-slate-900">
                      {deviceType} <span className="text-xs font-medium text-slate-600">({groupDevices.length})</span>
                    </h6>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Expand group first
                      if (!isExpanded) {
                        setExpandedGroups((prev) => new Set([...prev, deviceType]));
                      }
                      // Select all devices in this group
                      const groupDeviceIds = groupDevices.map((d) => d.device_id);
                      const newSelection = [
                        ...selectedDeviceIds.filter((id) => !groupDeviceIds.includes(id)),
                        ...groupDeviceIds,
                      ];
                      onDeviceSelectionChange(newSelection);
                    }}
                    className="rounded border border-blue-500 bg-white px-2 py-1 text-xs text-blue-500 hover:bg-blue-50"
                  >
                    Select All
                  </button>
                </div>

                {/* Group Content */}
                {isExpanded && (
                  <div className="p-3">
                    {groupDevices.map((device) => {
                      const isChecked = selectedDeviceIds.includes(device.device_id);
                      return (
                        <div key={device.device_id} className="mb-2 flex items-center">
                          <input
                            type="checkbox"
                            id={`device-${device.device_id}`}
                            className="mr-2 size-4 cursor-pointer"
                            checked={isChecked}
                            onChange={(e) => handleDeviceToggle(device.device_id, e.target.checked)}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <label
                            htmlFor={`device-${device.device_id}`}
                            className="flex-1 cursor-pointer text-sm font-medium text-slate-900"
                            title={`${device.device_name} (${device.device_id})`}
                          >
                            {device.device_name}
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
      <small className="mt-1 block font-medium text-slate-700">
        <span>{selectedDeviceIds.length}</span> device(s) selected
      </small>
    </div>
  );
}

