/**
 * Hierarchical Device Selection Handler
 * Handles Site -> Device Type -> Device Sub Group -> Device selection
 */
class DeviceSelection {
    constructor() {
        this.selectedSite = null;
        this.selectedDeviceType = null;
        this.selectedDeviceSubGroup = null;
        this.selectedDevice = null;
        this.apiBaseUrl = '/tickets/api/';
        this.cachedMultiSelectStates = {};
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
    }
    
    setupEventListeners() {
        // Try multiple possible IDs for the site select
        const siteSelect = document.getElementById('asset-select') || 
                          document.getElementById('id_asset_code') ||
                          document.querySelector('select[name="asset_code"]');
        const deviceTypeSelect = document.getElementById('device-type-select');
        const deviceSelect = document.getElementById('device-select') ||
                            document.getElementById('id_device_id') ||
                            document.querySelector('select[name="device_id"]');
        
        if (siteSelect) {
            siteSelect.addEventListener('change', (e) => {
                console.log('Site select changed:', e.target.value);
                this.onSiteChange(e.target.value);
            });
            // Only load sites if the select is empty (not pre-populated)
            if (siteSelect.options.length <= 1) {
                console.log('Loading sites via API...');
                this.loadSites();
            } else {
                console.log('Sites already populated, count:', siteSelect.options.length);
                // If sites are already loaded, trigger change if a value is selected
                if (siteSelect.value) {
                    console.log('Triggering onSiteChange for pre-selected site:', siteSelect.value);
                    this.onSiteChange(siteSelect.value);
                }
            }
        } else {
            console.error('Site select element not found!');
        }
        
        if (deviceTypeSelect) {
            deviceTypeSelect.addEventListener('change', (e) => {
                this.onDeviceTypeChange(e.target.value);
            });
        }
        
        if (deviceSelect) {
            deviceSelect.addEventListener('change', (e) => {
                console.log('Device select changed:', e.target.value);
                this.onDeviceChange(e.target.value);
            });
        }
        
        const subDeviceSelect = document.getElementById('sub-device-select');
        if (subDeviceSelect) {
            subDeviceSelect.addEventListener('change', (e) => {
                console.log('Sub device select changed:', e.target.value);
                // Update hidden sub_device_id field
                const subDeviceIdHidden = document.getElementById('sub-device-id-hidden') || document.getElementById('id_sub_device_id');
                if (subDeviceIdHidden) {
                    subDeviceIdHidden.value = e.target.value || '';
                }
            });
        }
    }
    
    async loadSites() {
        try {
            const response = await fetch(`${this.apiBaseUrl}sites/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // Try multiple possible IDs for the site select
            const siteSelect = document.getElementById('asset-select') || 
                              document.getElementById('id_asset_code') ||
                              document.querySelector('select[name="asset_code"]');
            if (!siteSelect) {
                console.error('Site select element not found');
                return;
            }
            
            // Clear existing options except the first one
            while (siteSelect.options.length > 1) {
                siteSelect.remove(1);
            }
            
            // Add sites
            data.sites.forEach(site => {
                const option = document.createElement('option');
                option.value = site.asset_code;
                option.textContent = `${site.asset_name} (${site.asset_code})`;
                siteSelect.appendChild(option);
            });
            
            // If there's a preselected value, trigger change
            if (siteSelect.value) {
                this.onSiteChange(siteSelect.value);
            }
        } catch (error) {
            console.error('Error loading sites:', error);
            this.showError('Failed to load sites. Please refresh the page.');
        }
    }
    
    async onSiteChange(siteCode) {
        console.log('Site changed to:', siteCode);
        if (!siteCode) {
            this.clearDeviceType();
            this.clearDeviceSubGroup();
            this.clearDevice();
            return;
        }
        
        this.selectedSite = siteCode;
        this.selectedDeviceType = null;
        this.selectedDeviceSubGroup = null;
        this.selectedDevice = null;
        
        // Update hidden fields
        this.updateHiddenField('device_type', '');
        this.updateHiddenField('device_sub_group', '');
        
        // Load device types
        try {
            await this.loadDeviceTypes(siteCode);
        } catch (error) {
            console.error('Error loading device types:', error);
            this.showError('Failed to load device types. Please try again.');
        }
        
        // Clear dependent fields
        this.clearDeviceSubGroup();
        this.clearDevice();
        this.clearSubDevice();
    }
    
    async loadDeviceTypes(siteCode) {
        try {
            const url = `${this.apiBaseUrl}device-types/?site=${encodeURIComponent(siteCode)}`;
            console.log('Loading device types from:', url);
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Device types response:', data);
            
            const deviceTypeSelect = document.getElementById('device-type-select');
            if (!deviceTypeSelect) {
                console.error('Device type select element not found');
                return;
            }
            
            // Clear existing options except the first one
            while (deviceTypeSelect.options.length > 1) {
                deviceTypeSelect.remove(1);
            }
            
            // Enable the select
            deviceTypeSelect.disabled = false;

            const multiSelectOptions = [];
            
            // Add device types
            if (data.device_types && data.device_types.length > 0) {
                data.device_types.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    deviceTypeSelect.appendChild(option);
                    multiSelectOptions.push({ value: type, label: type });
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No device types available';
                deviceTypeSelect.appendChild(option);
            }

            const hiddenDeviceType = document.getElementById('id_device_type') ||
                document.querySelector('input[name="device_type"]');
            let initialSelection = '';
            if (hiddenDeviceType && multiSelectOptions.some(opt => opt.value === hiddenDeviceType.value)) {
                initialSelection = hiddenDeviceType.value;
            } else if (deviceTypeSelect.value && multiSelectOptions.some(opt => opt.value === deviceTypeSelect.value)) {
                initialSelection = deviceTypeSelect.value;
            }

            if (initialSelection) {
                deviceTypeSelect.value = initialSelection;
                this.selectedDeviceType = initialSelection;
            } else {
                deviceTypeSelect.value = '';
                this.selectedDeviceType = null;
            }

            this.setMultiSelectState('deviceTypeMultiSelect', {
                options: multiSelectOptions,
                triggerId: 'deviceTypeFilterTrigger',
                placeholderId: 'deviceTypeFilterPlaceholder',
                enabledPlaceholder: 'Select Device Type',
                emptyPlaceholder: multiSelectOptions.length ? 'Select Device Type' : 'No device types available',
                selectedValues: initialSelection ? [initialSelection] : []
            });

            deviceTypeSelect.disabled = !multiSelectOptions.length;
        } catch (error) {
            console.error('Error loading device types:', error);
            this.showError('Failed to load device types.');
        }
    }
    
    async onDeviceTypeChange(deviceType) {
        if (!deviceType || !this.selectedSite) {
            this.clearDeviceSubGroup();
            this.clearDevice();
            return;
        }
        
        this.selectedDeviceType = deviceType;
        this.selectedDeviceSubGroup = null;
        this.selectedDevice = null;
        
        // Update hidden field
        this.updateHiddenField('device_type', deviceType);
        
        // Update visible select value
        const visibleSelect = document.getElementById('device-type-select');
        if (visibleSelect) {
            visibleSelect.value = deviceType;
        }
        
        // Load devices directly (filtered by device type only)
        await this.loadDevices(this.selectedSite, deviceType, null);
        
        // Clear device sub group and sub device
        this.clearDeviceSubGroup();
        this.clearSubDevice();
    }
    
    async loadDeviceSubGroups(siteCode, deviceType) {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}device-sub-groups/?site=${encodeURIComponent(siteCode)}&type=${encodeURIComponent(deviceType)}`
            );
            const data = await response.json();
            
            const deviceSubGroupSelect = document.getElementById('device-subgroup-select');
            if (!deviceSubGroupSelect) return;
            
            // Clear existing options except the first one
            while (deviceSubGroupSelect.options.length > 1) {
                deviceSubGroupSelect.remove(1);
            }
            
            // Enable the select
            deviceSubGroupSelect.disabled = false;
            
            // Add device sub groups
            if (data.device_sub_groups && data.device_sub_groups.length > 0) {
                data.device_sub_groups.forEach(subGroup => {
                    const option = document.createElement('option');
                    option.value = subGroup;
                    option.textContent = subGroup;
                    deviceSubGroupSelect.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No device sub groups available';
                deviceSubGroupSelect.appendChild(option);
            }
        } catch (error) {
            console.error('Error loading device sub groups:', error);
            this.showError('Failed to load device sub groups.');
        }
    }
    
    async onDeviceSubGroupChange(deviceSubGroup) {
        // This function is no longer used in the new flow
        // Devices are loaded directly after device type selection
        // Device sub group is auto-populated when device is selected
    }
    
    async loadDevices(siteCode, deviceType, deviceSubGroup) {
        try {
            const url = new URL(`${this.apiBaseUrl}devices/`, window.location.origin);
            url.searchParams.append('site', siteCode);
            if (deviceType) url.searchParams.append('type', deviceType);
            if (deviceSubGroup) url.searchParams.append('subgroup', deviceSubGroup);
            
            console.log('Loading devices from:', url.toString());
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Devices response:', data);
            
            const deviceSelect = document.getElementById('device-select');
            if (!deviceSelect) {
                console.error('Device select element not found');
                return;
            }
            
            // Clear existing options except the first one
            while (deviceSelect.options.length > 1) {
                deviceSelect.remove(1);
            }
            
            // Enable the select
            deviceSelect.disabled = false;

            const multiSelectOptions = [];
            
            // Add devices
            if (data.devices && data.devices.length > 0) {
                data.devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.device_id;
                    option.textContent = `${device.device_name} (${device.device_code})`;
                    option.dataset.deviceType = device.device_type;
                    option.dataset.deviceSubGroup = device.device_sub_group;
                    deviceSelect.appendChild(option);
                    multiSelectOptions.push({
                        value: device.device_id,
                        label: `${device.device_name} (${device.device_code})`
                    });
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No devices available';
                deviceSelect.appendChild(option);
            }

            const hiddenDeviceId = document.getElementById('device-id-hidden') ||
                document.getElementById('id_device_id') ||
                document.querySelector('input[name="device_id"]');
            let initialSelection = '';
            if (hiddenDeviceId && multiSelectOptions.some(opt => opt.value === hiddenDeviceId.value)) {
                initialSelection = hiddenDeviceId.value;
            } else if (deviceSelect.value && multiSelectOptions.some(opt => opt.value === deviceSelect.value)) {
                initialSelection = deviceSelect.value;
            }

            if (initialSelection) {
                deviceSelect.value = initialSelection;
                this.selectedDevice = initialSelection;
            } else {
                deviceSelect.value = '';
                this.selectedDevice = null;
            }

            this.setMultiSelectState('deviceMultiSelect', {
                options: multiSelectOptions,
                triggerId: 'deviceFilterTrigger',
                placeholderId: 'deviceFilterPlaceholder',
                enabledPlaceholder: 'Select Device',
                emptyPlaceholder: multiSelectOptions.length ? 'Select Device' : 'No devices available',
                selectedValues: initialSelection ? [initialSelection] : []
            });

            deviceSelect.disabled = !multiSelectOptions.length;

            deviceSelect.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (error) {
            console.error('Error loading devices:', error);
            this.showError('Failed to load devices.');
        }
    }
    
    async onDeviceChange(deviceId) {
        this.selectedDevice = deviceId;
        
        // Update device type and sub group from selected device
        const deviceSelect = document.getElementById('device-select');
        if (deviceSelect && deviceSelect.value) {
            const selectedOption = deviceSelect.options[deviceSelect.selectedIndex];
            if (selectedOption.dataset.deviceType) {
                this.updateHiddenField('device_type', selectedOption.dataset.deviceType);
            }
            if (selectedOption.dataset.deviceSubGroup) {
                const deviceSubGroup = selectedOption.dataset.deviceSubGroup;
                // Update hidden field
                this.updateHiddenField('device_sub_group', deviceSubGroup);
                this.selectedDeviceSubGroup = deviceSubGroup;
            }
            
            // Update hidden device_id field for form submission
            const deviceIdHidden = document.getElementById('device-id-hidden') || document.getElementById('id_device_id');
            if (deviceIdHidden) {
                deviceIdHidden.value = deviceId;
            }
            
            // Load sub devices where device_sub_group = selected device_id
            if (deviceId) {
                await this.loadSubDevices(this.selectedSite, deviceId);
            }
        } else {
            // Clear device sub group when no device is selected
            this.updateHiddenField('device_sub_group', '');
            this.selectedDeviceSubGroup = null;
            // Clear hidden device_id field
            const deviceIdHidden = document.getElementById('device-id-hidden') || document.getElementById('id_device_id');
            if (deviceIdHidden) {
                deviceIdHidden.value = '';
            }
            // Clear sub device dropdown
            this.clearSubDevice();
        }
    }
    
    async loadSubDevices(siteCode, parentDeviceId) {
        try {
            // Get the device_sub_group value from the selected device
            const deviceSelect = document.getElementById('device-select');
            if (!deviceSelect || !deviceSelect.value) {
                this.clearSubDevice();
                return;
            }
            
            // Load devices where device_sub_group equals the selected device_id
            const url = new URL(`${this.apiBaseUrl}devices/`, window.location.origin);
            url.searchParams.append('site', siteCode);
            url.searchParams.append('subgroup', parentDeviceId); // Filter by device_sub_group = device_id
            
            console.log('Loading sub devices from:', url.toString());
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Sub devices response:', data);
            
            const subDeviceSelect = document.getElementById('sub-device-select');
            if (!subDeviceSelect) {
                console.error('Sub device select element not found');
                return;
            }
            
            // Clear existing options except the first one
            while (subDeviceSelect.options.length > 1) {
                subDeviceSelect.remove(1);
            }
            
            // Enable the select
            subDeviceSelect.disabled = false;
            
            const multiSelectOptions = [];
            
            // Add sub devices (API already filters by device_sub_group = parentDeviceId)
            if (data.devices && data.devices.length > 0) {
                data.devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.device_id;
                    option.textContent = `${device.device_name} (${device.device_code})`;
                    subDeviceSelect.appendChild(option);
                    multiSelectOptions.push({
                        value: device.device_id,
                        label: `${device.device_name} (${device.device_code})`
                    });
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No sub devices available';
                subDeviceSelect.appendChild(option);
                subDeviceSelect.disabled = true;
            }

            const hiddenSubDeviceId = document.getElementById('sub-device-id-hidden') ||
                document.getElementById('id_sub_device_id') ||
                document.querySelector('input[name="sub_device_id"]');
            let initialSelection = '';
            if (hiddenSubDeviceId && multiSelectOptions.some(opt => opt.value === hiddenSubDeviceId.value)) {
                initialSelection = hiddenSubDeviceId.value;
            } else if (subDeviceSelect.value && multiSelectOptions.some(opt => opt.value === subDeviceSelect.value)) {
                initialSelection = subDeviceSelect.value;
            }

            if (initialSelection) {
                subDeviceSelect.value = initialSelection;
            } else {
                subDeviceSelect.value = '';
                if (hiddenSubDeviceId) {
                    hiddenSubDeviceId.value = '';
                }
            }

            this.setMultiSelectState('subDeviceMultiSelect', {
                options: multiSelectOptions,
                triggerId: 'subDeviceFilterTrigger',
                placeholderId: 'subDeviceFilterPlaceholder',
                enabledPlaceholder: 'Select Sub Device',
                emptyPlaceholder: multiSelectOptions.length ? 'Select Sub Device' : 'No sub devices available',
                selectedValues: initialSelection ? [initialSelection] : []
            });

            subDeviceSelect.disabled = !multiSelectOptions.length;

            subDeviceSelect.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (error) {
            console.error('Error loading sub devices:', error);
            this.showError('Failed to load sub devices.');
            this.clearSubDevice();
        }
    }
    
    clearSubDevice() {
        const subDeviceSelect = document.getElementById('sub-device-select');
        if (subDeviceSelect) {
            while (subDeviceSelect.options.length > 1) {
                subDeviceSelect.remove(1);
            }
            subDeviceSelect.disabled = true;
            subDeviceSelect.value = '';
            subDeviceSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
        // Clear hidden sub_device_id field
        const subDeviceIdHidden = document.getElementById('sub-device-id-hidden') || document.getElementById('id_sub_device_id');
        if (subDeviceIdHidden) {
            subDeviceIdHidden.value = '';
        }
        this.setMultiSelectState('subDeviceMultiSelect', {
            options: [],
            triggerId: 'subDeviceFilterTrigger',
            placeholderId: 'subDeviceFilterPlaceholder',
            enabledPlaceholder: 'Select Sub Device',
            emptyPlaceholder: 'Select device name first'
        });
    }
    
    clearDeviceType() {
        const deviceTypeSelect = document.getElementById('device-type-select');
        if (deviceTypeSelect) {
            while (deviceTypeSelect.options.length > 1) {
                deviceTypeSelect.remove(1);
            }
            deviceTypeSelect.disabled = true;
            deviceTypeSelect.value = '';
            deviceTypeSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
        this.setMultiSelectState('deviceTypeMultiSelect', {
            options: [],
            triggerId: 'deviceTypeFilterTrigger',
            placeholderId: 'deviceTypeFilterPlaceholder',
            enabledPlaceholder: 'Select Device Type',
            emptyPlaceholder: 'Select site first'
        });
        this.updateHiddenField('device_type', '');
    }
    
    clearDeviceSubGroup() {
        // Clear the hidden field
        this.updateHiddenField('device_sub_group', '');
        // Clear the display field
        const deviceSubGroupDisplay = document.getElementById('device-subgroup-display');
        if (deviceSubGroupDisplay) {
            deviceSubGroupDisplay.value = '';
        }
        this.selectedDeviceSubGroup = null;
    }
    
    clearDevice() {
        const deviceSelect = document.getElementById('device-select');
        if (deviceSelect) {
            while (deviceSelect.options.length > 1) {
                deviceSelect.remove(1);
            }
            deviceSelect.disabled = true;
            deviceSelect.value = '';
            deviceSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
        this.setMultiSelectState('deviceMultiSelect', {
            options: [],
            triggerId: 'deviceFilterTrigger',
            placeholderId: 'deviceFilterPlaceholder',
            enabledPlaceholder: 'Select Device',
            emptyPlaceholder: 'Select device type first'
        });
        const deviceIdHidden = document.getElementById('device-id-hidden') ||
            document.getElementById('id_device_id') ||
            document.querySelector('input[name="device_id"]');
        if (deviceIdHidden) {
            deviceIdHidden.value = '';
        }
    }
    
    updateHiddenField(fieldName, value) {
        const normalizedName = fieldName.startsWith('device_') ? fieldName : `device_${fieldName}`;
        let hiddenField = document.getElementById(`id_${normalizedName}`);
        if (!hiddenField) {
            hiddenField = document.querySelector(`input[name="${normalizedName}"]`);
        }
        if (hiddenField) {
            hiddenField.value = value;
        }
    }

    setMultiSelectState(instanceName, config = {}) {
        const normalizedConfig = {
            options: Array.isArray(config.options) ? [...config.options] : [],
            triggerId: config.triggerId || null,
            placeholderId: config.placeholderId || null,
            enabledPlaceholder: config.enabledPlaceholder || null,
            emptyPlaceholder: config.emptyPlaceholder || null,
            selectedValues: Array.isArray(config.selectedValues) ? [...config.selectedValues] : [],
            enableWhenOptions: config.enableWhenOptions !== undefined ? config.enableWhenOptions : true
        };

        this.cachedMultiSelectStates[instanceName] = normalizedConfig;

        const {
            options,
            triggerId,
            placeholderId,
            enabledPlaceholder,
            emptyPlaceholder,
            selectedValues,
            enableWhenOptions
        } = normalizedConfig;

        const multi = window[instanceName];
        const trigger = triggerId ? document.getElementById(triggerId) : null;
        const placeholder = placeholderId ? document.getElementById(placeholderId) : null;
        const hasOptions = Array.isArray(options) && options.length > 0;
        const shouldEnable = enableWhenOptions && hasOptions;
        const placeholderText = shouldEnable
            ? (enabledPlaceholder || (placeholder && placeholder.dataset.default) || '')
            : (emptyPlaceholder || (placeholder && placeholder.dataset.default) || '');

        if (multi) {
            multi.setOptions(options);

            if (Array.isArray(selectedValues)) {
                multi.setSelectedValues(selectedValues);
            }

            if (typeof multi.setEnabled === 'function') {
                multi.setEnabled(shouldEnable);
            }

            if (placeholder) {
                placeholder.dataset.default = placeholderText || '';
            }

            if (typeof multi.updateDisplay === 'function') {
                multi.updateDisplay();
            }
        } else if (placeholder) {
            placeholder.dataset.default = placeholderText || '';
        }

        if (placeholder) {
            placeholder.textContent = placeholder.dataset.default || placeholder.textContent || '';
        }

        if (trigger) {
            trigger.classList.toggle('disabled', !shouldEnable);
            trigger.style.pointerEvents = shouldEnable ? 'auto' : 'none';
            trigger.style.opacity = shouldEnable ? '1' : '0.6';
        }
    }

    applyMultiSelectState(instanceName) {
        const cachedConfig = this.cachedMultiSelectStates[instanceName];
        if (!cachedConfig) {
            return;
        }
        this.setMultiSelectState(instanceName, cachedConfig);
    }
    
    showError(message) {
        // Use Bootstrap alert or console
        if (typeof showToast !== 'undefined') {
            showToast(message, 'error');
        } else {
            console.error(message);
            alert(message);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check for any of the possible select element IDs
    const siteSelect = document.getElementById('asset-select') || 
                      document.getElementById('id_asset_code') ||
                      document.querySelector('select[name="asset_code"]');
    if (siteSelect) {
        window.deviceSelection = new DeviceSelection();
    }
});

