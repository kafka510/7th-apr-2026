"""
PV Module and Device Configuration API Views

This module provides API endpoints for:
- PV module datasheet management (CRUD operations)
- Device PV configuration management
- CSV import/export for bulk operations
"""
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.exceptions import ValidationError
from main.decorators.cors_decorator import cors_allow_same_site

import json
import csv
import io
import logging
from datetime import datetime

from accounts.decorators import feature_required
from main.models import (
    PVModuleDatasheet,
    PowerModelRegistry,
    device_list,
)
from main.permissions import user_has_capability

logger = logging.getLogger(__name__)


# ==========================================
# PV MODULE DATASHEET APIs
# ==========================================

@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_pv_modules_list(request):
    """
    Get list of all PV module datasheets
    
    Query params:
        - search: Search by manufacturer or model name
        - technology: Filter by technology type
    
    Returns:
        JSON array of module datasheets
    """
    try:
        # Base query
        modules = PVModuleDatasheet.objects.all()
        
        # Apply filters
        search = request.GET.get('search')
        if search:
            modules = modules.filter(
                module_model__icontains=search
            ) | modules.filter(
                manufacturer__icontains=search
            )
        
        technology = request.GET.get('technology')
        if technology:
            modules = modules.filter(technology=technology)
        
        # Serialize data - return ALL fields for editing
        modules_data = []
        for module in modules:
            modules_data.append({
                'id': module.id,
                'module_model': module.module_model,
                'manufacturer': module.manufacturer,
                'technology': module.technology,
                # STC Electrical Characteristics
                'pmax_stc': module.pmax_stc,
                'voc_stc': module.voc_stc,
                'isc_stc': module.isc_stc,
                'vmp_stc': module.vmp_stc,
                'imp_stc': module.imp_stc,
                'module_efficiency_stc': module.module_efficiency_stc,
                'noct': module.noct,
                # Temperature Coefficients
                'temp_coeff_pmax': module.temp_coeff_pmax,
                'temp_coeff_voc': module.temp_coeff_voc,
                'temp_coeff_isc': module.temp_coeff_isc,
                'temp_coeff_type_voc': module.temp_coeff_type_voc,
                'temp_coeff_type_isc': module.temp_coeff_type_isc,
                # Physical Characteristics
                'cells_per_module': module.cells_per_module,
                'length': module.length,
                'width': module.width,
                'area': module.area,
                # Low Irradiance Performance
                'low_irr_200': module.low_irr_200,
                'low_irr_400': module.low_irr_400,
                'low_irr_600': module.low_irr_600,
                'low_irr_800': module.low_irr_800,
                # Warranty & Degradation
                'warranty_year_1': module.warranty_year_1,
                'warranty_year_25': module.warranty_year_25,
                'linear_degradation_rate': module.linear_degradation_rate,
                # Computed properties
                'fill_factor': module.fill_factor,
                'estimated_degradation_year1': module.estimated_degradation_year1,
                'estimated_annual_degradation': module.estimated_annual_degradation,
                # Timestamps
                'created_at': module.created_at.isoformat(),
                'updated_at': module.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'count': len(modules_data),
            'modules': modules_data
        })
        
    except Exception as e:
        logger.error(f"Error in api_pv_modules_list: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_pv_module_detail(request, module_id):
    """
    Get detailed information for a single PV module datasheet
    
    Args:
        module_id: PV module datasheet ID
    
    Returns:
        JSON with complete module datasheet information
    """
    try:
        module = PVModuleDatasheet.objects.get(id=module_id)
        
        # Return all fields
        data = {
            'id': module.id,
            'module_model': module.module_model,
            'manufacturer': module.manufacturer,
            'technology': module.technology,
            # STC electrical
            'pmax_stc': module.pmax_stc,
            'isc_stc': module.isc_stc,
            'imp_stc': module.imp_stc,
            'voc_stc': module.voc_stc,
            'vmp_stc': module.vmp_stc,
            'module_efficiency_stc': module.module_efficiency_stc,
            # NOCT
            'noct': module.noct,
            # Temperature coefficients
            'temp_coeff_pmax': module.temp_coeff_pmax,
            'temp_coeff_voc': module.temp_coeff_voc,
            'temp_coeff_isc': module.temp_coeff_isc,
            'temp_coeff_type_voc': module.temp_coeff_type_voc,
            'temp_coeff_type_isc': module.temp_coeff_type_isc,
            # Physical
            'cells_per_module': module.cells_per_module,
            'length': module.length,
            'width': module.width,
            'area': module.area,
            # Low irradiance
            'low_irr_200': module.low_irr_200,
            'low_irr_400': module.low_irr_400,
            'low_irr_600': module.low_irr_600,
            'low_irr_800': module.low_irr_800,
            # Warranty
            'warranty_year_1': module.warranty_year_1,
            'warranty_year_25': module.warranty_year_25,
            'linear_degradation_rate': module.linear_degradation_rate,
            # Calculated properties
            'fill_factor': module.fill_factor,
            'estimated_degradation_year1': module.estimated_degradation_year1,
            'estimated_annual_degradation': module.estimated_annual_degradation,
            # Metadata
            'created_at': module.created_at.isoformat(),
            'updated_at': module.updated_at.isoformat(),
            'created_by': module.created_by.username if module.created_by else None,
        }
        
        return JsonResponse({
            'success': True,
            'module': data
        })
        
    except PVModuleDatasheet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Module not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in api_pv_module_detail: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["POST"])
@cors_allow_same_site
def api_create_pv_module(request):
    """
    Create new PV module datasheet
    
    POST data (JSON):
        Required:
            - module_model: Unique model name
            - manufacturer: Manufacturer name
            - pmax_stc, voc_stc, isc_stc, vmp_stc, imp_stc
            - module_efficiency_stc
            - temp_coeff_pmax, temp_coeff_voc, temp_coeff_isc
            - cells_per_module
            - length, width, area
        Optional:
            - technology, noct
            - Low irradiance values
            - Warranty data
            - etc.
    
    Returns:
        JSON with created module ID
    """
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required = [
            'module_model', 'manufacturer',
            'pmax_stc', 'voc_stc', 'isc_stc', 'vmp_stc', 'imp_stc',
            'module_efficiency_stc',
            'temp_coeff_pmax', 'temp_coeff_voc', 'temp_coeff_isc',
            'cells_per_module',
            'length', 'width', 'area'
        ]
        
        missing = [field for field in required if field not in data or data[field] is None]
        if missing:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }, status=400)
        
        # Check if module already exists
        if PVModuleDatasheet.objects.filter(module_model=data['module_model']).exists():
            return JsonResponse({
                'success': False,
                'error': f'Module "{data["module_model"]}" already exists'
            }, status=400)
        
        # Create module
        module = PVModuleDatasheet.objects.create(
            module_model=data['module_model'],
            manufacturer=data['manufacturer'],
            technology=data.get('technology', 'mono_perc'),
            # STC electrical
            pmax_stc=data['pmax_stc'],
            isc_stc=data['isc_stc'],
            imp_stc=data['imp_stc'],
            voc_stc=data['voc_stc'],
            vmp_stc=data['vmp_stc'],
            module_efficiency_stc=data['module_efficiency_stc'],
            # NOCT
            noct=data.get('noct', 45.0),
            # Temperature coefficients
            temp_coeff_pmax=data['temp_coeff_pmax'],
            temp_coeff_voc=data['temp_coeff_voc'],
            temp_coeff_isc=data['temp_coeff_isc'],
            temp_coeff_type_voc=data.get('temp_coeff_type_voc', 'absolute'),
            temp_coeff_type_isc=data.get('temp_coeff_type_isc', 'percentage'),
            # Physical
            cells_per_module=data['cells_per_module'],
            length=data['length'],
            width=data['width'],
            area=data['area'],
            # Low irradiance
            low_irr_200=data.get('low_irr_200'),
            low_irr_400=data.get('low_irr_400'),
            low_irr_600=data.get('low_irr_600'),
            low_irr_800=data.get('low_irr_800'),
            # Warranty
            warranty_year_1=data.get('warranty_year_1'),
            warranty_year_25=data.get('warranty_year_25'),
            linear_degradation_rate=data.get('linear_degradation_rate'),
            # Metadata
            created_by=request.user
        )
        
        logger.info(f"Created PV module: {module.module_model} by user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'module_id': module.id,
            'message': f'Module "{module.module_model}" created successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_create_pv_module: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["PUT", "PATCH"])
@cors_allow_same_site
def api_update_pv_module(request, module_id):
    """
    Update existing PV module datasheet
    
    Args:
        module_id: Module ID to update
    
    POST data (JSON):
        Any PVModuleDatasheet fields to update
    
    Returns:
        JSON with success status
    """
    try:
        data = json.loads(request.body)
        
        # Get module
        module = PVModuleDatasheet.objects.get(id=module_id)
        
        # Update fields if provided
        updateable_fields = [
            'module_model', 'manufacturer', 'technology',
            'pmax_stc', 'isc_stc', 'imp_stc', 'voc_stc', 'vmp_stc',
            'module_efficiency_stc', 'noct',
            'temp_coeff_pmax', 'temp_coeff_voc', 'temp_coeff_isc',
            'temp_coeff_type_voc', 'temp_coeff_type_isc',
            'cells_per_module', 'length', 'width', 'area',
            'low_irr_200', 'low_irr_400', 'low_irr_600', 'low_irr_800',
            'warranty_year_1', 'warranty_year_25', 'linear_degradation_rate'
        ]
        
        updated_fields = []
        for field in updateable_fields:
            if field in data:
                setattr(module, field, data[field])
                updated_fields.append(field)
        
        # Check for duplicate module_model if being changed
        if 'module_model' in data and data['module_model'] != module.module_model:
            if PVModuleDatasheet.objects.filter(module_model=data['module_model']).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Module "{data["module_model"]}" already exists'
                }, status=400)
        
        module.save()
        
        logger.info(f"Updated PV module {module_id}: {', '.join(updated_fields)} by user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Module updated successfully',
            'updated_fields': updated_fields
        })
        
    except PVModuleDatasheet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Module not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_update_pv_module: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["DELETE"])
@cors_allow_same_site
def api_delete_pv_module(request, module_id):
    """
    Delete PV module datasheet
    
    **SUPERUSER ONLY**
    
    Checks if module is in use before deletion.
    If in use and force=true, unlinks devices first.
    
    Args:
        module_id: Module ID to delete
    
    Query params:
        - force: If 'true', unlink devices and delete anyway
    
    Returns:
        JSON with success status
    """
    try:
        # Check if user is superuser
        if not request.user.is_superuser:
            logger.warning(
                f"Non-superuser {request.user.username} attempted to delete "
                f"PV module {module_id}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Only superusers can delete module datasheets'
            }, status=403)
        
        # Get module
        module = PVModuleDatasheet.objects.get(id=module_id)
        
        # Check if module is in use
        devices_using = device_list.objects.filter(module_datasheet_id=module_id).count()
        
        if devices_using > 0:
            force = request.GET.get('force', '').lower() == 'true'
            
            if not force:
                return JsonResponse({
                    'success': False,
                    'error': f'Module is in use by {devices_using} device(s). Use force=true to unlink and delete.',
                    'devices_count': devices_using,
                    'requires_confirmation': True
                }, status=400)
            
            # Unlink devices
            device_list.objects.filter(module_datasheet_id=module_id).update(
                module_datasheet_id=None
            )
            logger.warning(
                f"Unlinked {devices_using} devices from module {module.module_model} "
                f"by superuser {request.user.username}"
            )
        
        module_model = module.module_model
        module.delete()
        
        logger.info(f"Deleted PV module {module_model} by superuser {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Module "{module_model}" deleted successfully',
            'devices_unlinked': devices_using
        })
        
    except PVModuleDatasheet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Module not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in api_delete_pv_module: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["POST"])
@cors_allow_same_site
def api_import_pv_modules(request):
    """
    Import PV module datasheets from CSV file
    
    POST data (multipart/form-data):
        - file: CSV file
        - mode: 'create' (skip existing) or 'update' (update existing) or 'both'
    
    CSV format:
        module_model,manufacturer,technology,pmax_stc,voc_stc,isc_stc,...
    
    Returns:
        JSON with import summary
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file uploaded'
            }, status=400)
        
        csv_file = request.FILES['file']
        mode = request.POST.get('mode', 'create')  # 'create', 'update', or 'both'
        
        # Read CSV
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                module_model = row.get('module_model', '').strip()
                
                if not module_model:
                    errors.append(f"Row {row_num}: Missing module_model")
                    continue
                
                # Check if exists
                exists = PVModuleDatasheet.objects.filter(module_model=module_model).exists()
                
                if exists and mode == 'create':
                    skipped_count += 1
                    continue
                
                if not exists and mode == 'update':
                    skipped_count += 1
                    continue
                
                # Prepare data
                module_data = {
                    'module_model': module_model,
                    'manufacturer': row.get('manufacturer', '').strip(),
                    'technology': row.get('technology', 'mono_perc'),
                    'pmax_stc': float(row.get('pmax_stc', 0)),
                    'isc_stc': float(row.get('isc_stc', 0)),
                    'imp_stc': float(row.get('imp_stc', 0)),
                    'voc_stc': float(row.get('voc_stc', 0)),
                    'vmp_stc': float(row.get('vmp_stc', 0)),
                    'module_efficiency_stc': float(row.get('module_efficiency_stc', 0)),
                    'noct': float(row.get('noct', 45.0)),
                    'temp_coeff_pmax': float(row.get('temp_coeff_pmax', -0.35)),
                    'temp_coeff_voc': float(row.get('temp_coeff_voc', -0.27)),
                    'temp_coeff_isc': float(row.get('temp_coeff_isc', 0.048)),
                    'temp_coeff_type_voc': row.get('temp_coeff_type_voc', 'absolute'),
                    'temp_coeff_type_isc': row.get('temp_coeff_type_isc', 'percentage'),
                    'cells_per_module': int(row.get('cells_per_module', 144)),
                    'length': float(row.get('length', 2172)),
                    'width': float(row.get('width', 1103)),
                    'area': float(row.get('area', 2.4)),
                    'created_by': request.user
                }
                
                # Optional fields
                if row.get('low_irr_200'):
                    module_data['low_irr_200'] = float(row['low_irr_200'])
                if row.get('low_irr_400'):
                    module_data['low_irr_400'] = float(row['low_irr_400'])
                if row.get('low_irr_600'):
                    module_data['low_irr_600'] = float(row['low_irr_600'])
                if row.get('low_irr_800'):
                    module_data['low_irr_800'] = float(row['low_irr_800'])
                if row.get('warranty_year_1'):
                    module_data['warranty_year_1'] = float(row['warranty_year_1'])
                if row.get('warranty_year_25'):
                    module_data['warranty_year_25'] = float(row['warranty_year_25'])
                if row.get('linear_degradation_rate'):
                    module_data['linear_degradation_rate'] = float(row['linear_degradation_rate'])
                
                # Create or update
                if exists:
                    PVModuleDatasheet.objects.filter(module_model=module_model).update(**module_data)
                    updated_count += 1
                else:
                    PVModuleDatasheet.objects.create(**module_data)
                    created_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num} ({row.get('module_model', 'unknown')}): {str(e)}")
                continue
        
        logger.info(
            f"PV module CSV import by {request.user.username}: "
            f"{created_count} created, {updated_count} updated, "
            f"{skipped_count} skipped, {len(errors)} errors"
        )
        
        return JsonResponse({
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors,
            'total_processed': created_count + updated_count + skipped_count + len(errors)
        })
        
    except Exception as e:
        logger.error(f"Error in api_import_pv_modules: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_export_pv_modules(request):
    """
    Export PV module datasheets to CSV
    
    Returns:
        CSV file with all module datasheets
    """
    try:
        # Create response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pv_module_datasheets.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'module_model', 'manufacturer', 'technology',
            'pmax_stc', 'isc_stc', 'imp_stc', 'voc_stc', 'vmp_stc',
            'module_efficiency_stc', 'noct',
            'temp_coeff_pmax', 'temp_coeff_voc', 'temp_coeff_isc',
            'temp_coeff_type_voc', 'temp_coeff_type_isc',
            'cells_per_module', 'length', 'width', 'area',
            'low_irr_200', 'low_irr_400', 'low_irr_600', 'low_irr_800',
            'warranty_year_1', 'warranty_year_25', 'linear_degradation_rate'
        ])
        
        # Write data
        modules = PVModuleDatasheet.objects.all().order_by('manufacturer', 'module_model')
        
        for module in modules:
            writer.writerow([
                module.module_model,
                module.manufacturer,
                module.technology,
                module.pmax_stc,
                module.isc_stc,
                module.imp_stc,
                module.voc_stc,
                module.vmp_stc,
                module.module_efficiency_stc,
                module.noct,
                module.temp_coeff_pmax,
                module.temp_coeff_voc,
                module.temp_coeff_isc,
                module.temp_coeff_type_voc,
                module.temp_coeff_type_isc,
                module.cells_per_module,
                module.length,
                module.width,
                module.area,
                module.low_irr_200 or '',
                module.low_irr_400 or '',
                module.low_irr_600 or '',
                module.low_irr_800 or '',
                module.warranty_year_1 or '',
                module.warranty_year_25 or '',
                module.linear_degradation_rate or ''
            ])
        
        logger.info(f"Exported {modules.count()} PV modules to CSV by user {request.user.username}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in api_export_pv_modules: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==========================================
# DEVICE PV CONFIGURATION APIs
# ==========================================

@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_weather_metrics_list(request):
    """
    Get list of unique metrics available for weather devices (device_type='wst') for a specific asset.
    
    Query params:
        - asset_code: Asset code to filter metrics (required)
    
    Returns:
        JSON with list of unique metrics from device_mapping where device_type='wst' and asset_code matches
    """
    try:
        from main.models import device_mapping
        
        asset_code = request.GET.get('asset_code')
        
        if not asset_code:
            return JsonResponse({
                'success': False,
                'error': 'asset_code parameter is required'
            }, status=400)
        
        # Get unique metrics for device_type='wst' filtered by asset_code
        # Filter out blank/null/whitespace-only metrics and get distinct values
        from django.db.models import Q
        
        # Get all records first, then filter in Python to handle whitespace-only values
        all_metrics = device_mapping.objects.filter(
            device_type='wst',
            asset_code=asset_code
        ).exclude(
            Q(metric__isnull=True) | Q(metric='')
        ).values('metric', 'oem_tag', 'units', 'discription')
        
        # Filter out blanks and whitespace-only, then get unique metrics
        seen_metrics = {}
        for m in all_metrics:
            metric_value = m.get('metric', '').strip() if m.get('metric') else ''
            
            # Skip if blank or already seen
            if not metric_value or metric_value in seen_metrics:
                continue
            
            # Store first occurrence of each unique metric
            seen_metrics[metric_value] = {
                'metric': metric_value,
                'oem_tag': m.get('oem_tag', ''),
                'units': m.get('units', ''),
                'description': m.get('discription', '')
            }
        
        # Convert to sorted list
        metrics_list = sorted(seen_metrics.values(), key=lambda x: x['metric'])
        
        return JsonResponse({
            'success': True,
            'count': len(metrics_list),
            'metrics': metrics_list
        })
        
    except Exception as e:
        logger.error(f"Error in api_weather_metrics_list: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_weather_devices_list(request):
    """
    Get list of weather devices for a given asset.
    
    Query params:
        - asset_code: Asset code to filter devices
        - device_type: Optional filter for device type (weather, meteo, etc.)
    
    Returns:
        JSON with list of weather devices
    """
    try:
        asset_code = request.GET.get('asset_code')
        device_type_filter = request.GET.get('device_type', '')
        
        if not asset_code:
            return JsonResponse({
                'success': False,
                'error': 'asset_code is required'
            }, status=400)
        
        # Find weather devices for this asset
        # Primary: device_type = 'wst' (weather station)
        # Fallback: other weather-related patterns
        from django.db.models import Q
        
        devices_query = device_list.objects.filter(parent_code=asset_code)
        
        # Filter by device_type if provided
        if device_type_filter:
            devices_query = devices_query.filter(device_type__icontains=device_type_filter)
        else:
            # Primary: Look for device_type = 'wst' (exact match)
            # This is the main weather device type
            weather_filter = Q(device_type='wst')
            
            # Fallback: Also include other weather-related device types
            weather_types = ['weather', 'meteo', 'meteorological', 'pyranometer', 'irradiance', 'sensor']
            for weather_type in weather_types:
                weather_filter |= Q(device_type__icontains=weather_type)
            
            # Also search by device_id pattern as additional fallback
            id_filter = Q(device_id__icontains='wst') | Q(device_id__icontains='weather') | Q(device_id__icontains='meteo')
            
            # Combine: device_type matches OR device_id matches
            devices_query = devices_query.filter(weather_filter | id_filter)
        
        devices = devices_query.values('device_id', 'device_name', 'device_type').distinct()
        
        devices_list = [
            {
                'device_id': d['device_id'],
                'device_name': d['device_name'],
                'device_type': d['device_type']
            }
            for d in devices
        ]
        
        return JsonResponse({
            'success': True,
            'count': len(devices_list),
            'devices': devices_list
        })
        
    except Exception as e:
        logger.error(f"Error in api_weather_devices_list: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_device_pv_config_list(request):
    """
    Get list of devices with PV configuration
    
    Query params:
        - asset_code: Filter by asset
        - inverter_id: Filter by inverter (hierarchical)
        - jb_id: Filter by JB (hierarchical)
        - configured: 'true' for configured only, 'false' for unconfigured only
        - level: 'string' (default) or 'inverter'
    
    Returns:
        JSON array of devices with PV configuration
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        level = (request.GET.get('level') or 'string').strip().lower()

        # Common filters
        asset_code = request.GET.get('asset_code')
        inverter_id = request.GET.get('inverter_id')
        jb_id = request.GET.get('jb_id')
        configured = request.GET.get('configured')
        
        logger.info(f"PV config list filters - Level: {level}, Asset: {asset_code}, Inverter: {inverter_id}, JB: {jb_id}, Configured: {configured}")

        # ===========================
        # Inverter-level mode
        # ===========================
        if level == 'inverter':
            # Base query: inverter devices for the asset
            devices = device_list.objects.filter(
                device_type__icontains='_inv'
            )

            if asset_code:
                devices = devices.filter(parent_code=asset_code)

            # Optional filter by specific inverter_id(s)
            if inverter_id:
                inv_ids = [d.strip() for d in inverter_id.split(',') if d.strip()]
                if inv_ids:
                    devices = devices.filter(device_id__in=inv_ids)

            # Simple configured filter for inverters:
            # - 'true'  => has non-empty tilt_configs JSON
            # - 'false' => missing or empty tilt_configs
            if configured == 'true':
                devices = devices.exclude(tilt_configs__isnull=True)
            elif configured == 'false':
                devices = devices.filter(tilt_configs__isnull=True)

            logger.info(f"Inverter-level PV config list count: {devices.count()}")

            devices_data = []
            for inv in devices:
                power_model = inv.get_power_model()
                devices_data.append({
                    'device_id': inv.device_id,
                    'device_name': inv.device_name,
                    'device_type': inv.device_type,
                    'parent_code': inv.parent_code,
                    'module_datasheet_id': inv.module_datasheet_id,
                    'dc_cap': float(inv.dc_cap) if getattr(inv, 'dc_cap', None) is not None else None,
                    'ac_capacity': float(inv.ac_capacity) if getattr(inv, 'ac_capacity', None) is not None else None,
                    # Inverter-level SDM groups / tilt configs
                    'tilt_configs': getattr(inv, 'tilt_configs', None),
                    # Weather device configuration (with fallback support)
                    'weather_device_config': inv.weather_device_config if inv.weather_device_config else None,
                    # Power model at inverter level
                    'power_model_id': inv.power_model_id,
                    'power_model_name': power_model.model_name if power_model else None,
                    'model_fallback_enabled': inv.model_fallback_enabled if inv.model_fallback_enabled is not None else None,
                })

            return JsonResponse({
                'success': True,
                'count': len(devices_data),
                'devices': devices_data
            })

        # ===========================
        # String-level mode (default)
        # ===========================

        # Base query - only string devices
        devices = device_list.objects.filter(
            device_type__icontains='string'
        )
        
        logger.info(f"Initial string devices count: {devices.count()}")
        
        if asset_code:
            devices = devices.filter(parent_code=asset_code)
            logger.info(f"After asset filter: {devices.count()} devices")
        
        # Hierarchical filtering - only apply inverter filter if NO JB specified
        # (JB filter is more specific and already implies the inverter)
        if inverter_id and not jb_id:
            # Support multiple inverters (comma-separated)
            inverter_ids = [id.strip() for id in inverter_id.split(',') if id.strip()]
            if inverter_ids:
                from django.db.models import Q
                inverter_filter = Q()
                for inv_id in inverter_ids:
                    # Strings have device_sub_group = inverter's device_id
                    inverter_filter |= Q(device_sub_group=inv_id)
                devices = devices.filter(inverter_filter)
                logger.info(f"After inverter filter ({len(inverter_ids)} inverters): {devices.count()} devices")
        
        # Hierarchical filtering by JB(s) - most specific level
        if jb_id:
            # Support multiple JBs (comma-separated)
            jb_ids = [id.strip() for id in jb_id.split(',') if id.strip()]
            logger.info(f"JB IDs to filter: {jb_ids}")
            if jb_ids:
                from django.db.models import Q
                jb_filter = Q()
                for j_id in jb_ids:
                    # Strings have device_sub_group = JB's device_id
                    jb_filter |= Q(device_sub_group=j_id)
                    logger.info(f"Looking for strings with device_sub_group = {j_id}")
                
                before_jb_count = devices.count()
                devices = devices.filter(jb_filter)
                after_jb_count = devices.count()
                logger.info(f"JB filter: {before_jb_count} -> {after_jb_count} devices")
                
                # Debug: Show sample devices
                if after_jb_count > 0:
                    sample = devices.first()
                    logger.info(f"Sample device: {sample.device_id}, device_sub_group: {sample.device_sub_group}")
                else:
                    logger.warning(f"No strings found with device_sub_group in {jb_ids}")
                    # Debug: Check what device_sub_groups exist
                    existing_groups = device_list.objects.filter(
                        parent_code=asset_code,
                        device_type__icontains='string'
                    ).values_list('device_sub_group', flat=True).distinct()[:10]
                    logger.warning(f"Sample existing device_sub_groups: {list(existing_groups)}")
        
        # Filter by configuration status
        if configured == 'true':
            devices = devices.exclude(module_datasheet_id__isnull=True)
            logger.info(f"After configured filter: {devices.count()} devices")
        elif configured == 'false':
            devices = devices.filter(module_datasheet_id__isnull=True)
            logger.info(f"After unconfigured filter: {devices.count()} devices")
        
        # Serialize data
        devices_data = []
        for device in devices:
            # Manually fetch related objects
            module = device.get_module_datasheet()
            power_model = device.get_power_model()

            # Loss calculation enable flag: default to True when null (backward compatible)
            loss_enabled = device.loss_calculation_enabled
            if loss_enabled is None:
                loss_enabled = True

            devices_data.append({
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_type': device.device_type,
                'parent_code': device.parent_code,
                # Module configuration
                'module_datasheet_id': device.module_datasheet_id,
                'module_model': module.module_model if module else None,
                'manufacturer': module.manufacturer if module else None,
                'pmax_stc': module.pmax_stc if module else None,
                # Configuration
                'modules_in_series': device.modules_in_series,
                'installation_date': device.installation_date.isoformat() if device.installation_date else None,
                'tilt_angle': float(device.tilt_angle) if device.tilt_angle else None,
                'azimuth_angle': float(device.azimuth_angle) if device.azimuth_angle else None,
                'mounting_type': device.mounting_type,
                'expected_soiling_loss': float(device.expected_soiling_loss) if device.expected_soiling_loss is not None else None,
                'shading_factor': float(device.shading_factor) if device.shading_factor is not None else None,
                'measured_degradation_rate': float(device.measured_degradation_rate) if device.measured_degradation_rate else None,
                'last_performance_test_date': device.last_performance_test_date.isoformat() if device.last_performance_test_date else None,
                'operational_notes': device.operational_notes,
                # Power model
                'power_model_id': device.power_model_id,
                'power_model_name': power_model.model_name if power_model else None,
                'model_fallback_enabled': device.model_fallback_enabled if device.model_fallback_enabled is not None else None,
                # Weather device configuration
                'weather_device_config': device.weather_device_config if device.weather_device_config else None,
                # Loss calculation enable flag for UI
                'loss_calculation_enabled': loss_enabled,
                # Calculated values
                'string_rated_power': device.string_rated_power,
                'string_voc': device.string_voc,
                'string_vmp': device.string_vmp,
                'string_age_years': device.string_age_years,
                'current_degradation_factor': device.current_degradation_factor,
            })
        
        logger.info(f"Returning {len(devices_data)} devices to frontend")
        return JsonResponse({
            'success': True,
            'count': len(devices_data),
            'devices': devices_data
        })
        
    except Exception as e:
        logger.error(f"Error in api_device_pv_config_list: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_device_pv_config_get(request):
    """
    Get a single device's PV configuration by device_id.
    Used by the inverter config modal to load tilt_configs and other fields from device_list.
    """
    device_id = (request.GET.get('device_id') or '').strip()
    if not device_id:
        return JsonResponse({'success': False, 'error': 'device_id is required'}, status=400)
    try:
        dev = device_list.objects.filter(device_id=device_id).first()
        if not dev:
            return JsonResponse({'success': False, 'error': f'Device {device_id} not found'}, status=404)
        is_inverter = '_inv' in (dev.device_type or '')
        if is_inverter:
            power_model = dev.get_power_model()
            device_data = {
                'device_id': dev.device_id,
                'device_name': dev.device_name,
                'device_type': dev.device_type,
                'parent_code': dev.parent_code,
                'module_datasheet_id': dev.module_datasheet_id,
                'dc_cap': float(dev.dc_cap) if getattr(dev, 'dc_cap', None) is not None else None,
                'ac_capacity': float(dev.ac_capacity) if getattr(dev, 'ac_capacity', None) is not None else None,
                'tilt_configs': dev.tilt_configs,
                'weather_device_config': dev.weather_device_config if dev.weather_device_config else None,
                'power_model_id': dev.power_model_id,
                'power_model_name': power_model.model_name if power_model else None,
                'model_fallback_enabled': dev.model_fallback_enabled if dev.model_fallback_enabled is not None else None,
            }
        else:
            module = dev.get_module_datasheet()
            power_model = dev.get_power_model()

            # Loss calculation enable flag: default to True when null (backward compatible)
            loss_enabled = dev.loss_calculation_enabled
            if loss_enabled is None:
                loss_enabled = True

            device_data = {
                'device_id': dev.device_id,
                'device_name': dev.device_name,
                'device_type': dev.device_type,
                'parent_code': dev.parent_code,
                'module_datasheet_id': dev.module_datasheet_id,
                'modules_in_series': dev.modules_in_series,
                'tilt_angle': float(dev.tilt_angle) if dev.tilt_angle is not None else None,
                'azimuth_angle': float(dev.azimuth_angle) if dev.azimuth_angle is not None else None,
                'weather_device_config': dev.weather_device_config if dev.weather_device_config else None,
                'power_model_id': dev.power_model_id,
                'tilt_configs': getattr(dev, 'tilt_configs', None),
                # Loss calculation enable flag for UI
                'loss_calculation_enabled': loss_enabled,
            }
            if module:
                device_data['module_model'] = module.model_name
                device_data['manufacturer'] = module.manufacturer
            if power_model:
                device_data['power_model_name'] = power_model.model_name
        return JsonResponse({'success': True, 'device': device_data})
    except Exception as e:
        logger.error(f"Error in api_device_pv_config_get: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["POST"])
@cors_allow_same_site
def api_update_device_pv_config(request):
    """
    Update PV configuration for a single device
    
    POST data (JSON):
        - device_id: Device ID to update
        - Configuration fields to update (any of the PV module fields)
    
    Returns:
        JSON with success status
    """
    try:
        data = json.loads(request.body)
        
        device_id = data.get('device_id')
        if not device_id:
            return JsonResponse({
                'success': False,
                'error': 'device_id is required'
            }, status=400)
        
        # Get device
        device = device_list.objects.get(device_id=device_id)
        
        # Update fields if provided
        updated_fields = []
        
        if 'module_datasheet_id' in data:
            # Validate module exists
            if data['module_datasheet_id']:
                if not PVModuleDatasheet.objects.filter(id=data['module_datasheet_id']).exists():
                    return JsonResponse({
                        'success': False,
                        'error': f"Module datasheet ID {data['module_datasheet_id']} not found"
                    }, status=400)
            device.module_datasheet_id = data['module_datasheet_id']
            updated_fields.append('module_datasheet_id')
        
        if 'modules_in_series' in data:
            device.modules_in_series = data['modules_in_series']
            updated_fields.append('modules_in_series')

        if 'loss_calculation_enabled' in data:
            device.loss_calculation_enabled = data['loss_calculation_enabled']
            updated_fields.append('loss_calculation_enabled')
        
        if 'installation_date' in data:
            device.installation_date = data['installation_date'] if data['installation_date'] else None
            updated_fields.append('installation_date')
        
        if 'tilt_angle' in data:
            device.tilt_angle = data['tilt_angle']
            updated_fields.append('tilt_angle')
        
        if 'azimuth_angle' in data:
            device.azimuth_angle = data['azimuth_angle']
            updated_fields.append('azimuth_angle')
        
        if 'mounting_type' in data:
            device.mounting_type = data['mounting_type']
            updated_fields.append('mounting_type')
        
        if 'expected_soiling_loss' in data:
            device.expected_soiling_loss = data['expected_soiling_loss']
            updated_fields.append('expected_soiling_loss')
        
        if 'shading_factor' in data:
            device.shading_factor = data['shading_factor']
            updated_fields.append('shading_factor')
        
        if 'measured_degradation_rate' in data:
            device.measured_degradation_rate = data['measured_degradation_rate']
            updated_fields.append('measured_degradation_rate')
        
        if 'last_performance_test_date' in data:
            device.last_performance_test_date = data['last_performance_test_date'] if data['last_performance_test_date'] else None
            updated_fields.append('last_performance_test_date')
        
        if 'operational_notes' in data:
            device.operational_notes = data['operational_notes']
            updated_fields.append('operational_notes')
        
        if 'power_model_id' in data:
            power_model_id = data.get('power_model_id')
            if power_model_id is not None:
                # Validate power_model_id exists in database
                try:
                    power_model = PowerModelRegistry.objects.get(id=power_model_id, is_active=True)
                    device.power_model_id = power_model_id
                    updated_fields.append('power_model_id')
                except PowerModelRegistry.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': f'Power model with ID {power_model_id} not found or inactive. Please refresh the page and select a valid model.'
                    }, status=400)
            else:
                # Allow setting to None/null
                device.power_model_id = None
                updated_fields.append('power_model_id')
        
        if 'model_fallback_enabled' in data:
            device.model_fallback_enabled = data['model_fallback_enabled']
            updated_fields.append('model_fallback_enabled')
        
        if 'weather_device_config' in data:
            import json as json_module
            # Validate weather_device_config structure
            weather_config = data['weather_device_config']
            if weather_config:
                if not isinstance(weather_config, dict):
                    return JsonResponse({
                        'success': False,
                        'error': 'weather_device_config must be a JSON object'
                    }, status=400)
                # Validate structure
                valid_keys = ['irradiance_devices', 'temperature_devices', 'wind_devices']
                for key in weather_config.keys():
                    if key not in valid_keys:
                        return JsonResponse({
                            'success': False,
                            'error': f'Invalid key in weather_device_config: {key}. Valid keys: {valid_keys}'
                        }, status=400)
                    if not isinstance(weather_config[key], list):
                        return JsonResponse({
                            'success': False,
                            'error': f'{key} must be an array'
                        }, status=400)
                    
                    # Validate each item in the list
                    for item in weather_config[key]:
                        # Support both old format (string device IDs) and new format (device+metric objects)
                        if isinstance(item, str):
                            # Old format: just device ID (backward compatible)
                            continue
                        elif isinstance(item, dict):
                            # New format: must have device_id and metric
                            if 'device_id' not in item or 'metric' not in item:
                                return JsonResponse({
                                    'success': False,
                                    'error': f'{key} items must have "device_id" and "metric" fields when using object format'
                                }, status=400)
                        else:
                            return JsonResponse({
                                'success': False,
                                'error': f'{key} items must be either strings (device IDs) or objects with device_id and metric'
                            }, status=400)
            device.weather_device_config = weather_config
            updated_fields.append('weather_device_config')

        # Inverter-level SDM groups / tilt_configs
        if 'tilt_configs' in data:
            tilt_configs = data['tilt_configs']
            if tilt_configs is not None:
                if not isinstance(tilt_configs, list):
                    return JsonResponse({
                        'success': False,
                        'error': 'tilt_configs must be an array of objects or null'
                    }, status=400)
                for idx, cfg in enumerate(tilt_configs):
                    if not isinstance(cfg, dict):
                        return JsonResponse({
                            'success': False,
                            'error': f'tilt_configs[{idx}] must be an object'
                        }, status=400)
                    required_keys = ['tilt_deg', 'azimuth_deg', 'string_count', 'modules_in_series', 'panel_count']
                    for key in required_keys:
                        if key not in cfg:
                            return JsonResponse({
                                'success': False,
                                'error': f'tilt_configs[{idx}] missing required key: {key}'
                            }, status=400)
                    try:
                        tilt_val = float(cfg['tilt_deg'])
                        az_val = float(cfg['azimuth_deg'])
                        string_count = int(cfg['string_count'])
                        modules_in_series = int(cfg['modules_in_series'])
                        panel_count = int(cfg['panel_count'])
                    except (TypeError, ValueError):
                        return JsonResponse({
                            'success': False,
                            'error': f'tilt_configs[{idx}] has invalid numeric values'
                        }, status=400)
                    if string_count <= 0 or modules_in_series <= 0 or panel_count <= 0:
                        return JsonResponse({
                            'success': False,
                            'error': f'tilt_configs[{idx}] counts must be positive integers'
                        }, status=400)
                    # Basic consistency check: panel_count ≈ string_count * modules_in_series
                    expected_panels = string_count * modules_in_series
                    if expected_panels != panel_count:
                        logger.warning(
                            "tilt_configs[%d] panel_count (%d) does not equal string_count * modules_in_series (%d * %d = %d) "
                            "for device %s",
                            idx, panel_count, string_count, modules_in_series, expected_panels, device_id
                        )
            device.tilt_configs = tilt_configs
            updated_fields.append('tilt_configs')
        
        # Use raw SQL for unmanaged model
        from django.db import connection
        import json as json_module
        
        # SECURITY: Whitelist of allowed field names to prevent SQL injection
        ALLOWED_DEVICE_LIST_UPDATE_FIELDS = {
            'pv_module_config', 'model_fallback_enabled', 'weather_device_config', 'tilt_configs',
            'installation_date', 'last_performance_test_date', 'tilt_angle',
            'azimuth_angle', 'mounting_type', 'expected_soiling_loss', 'shading_factor',
            'measured_degradation_rate', 'operational_notes', 'power_model_id',
            'module_datasheet_id', 'modules_in_series', 'loss_calculation_enabled'
        }
        
        with connection.cursor() as cursor:
            update_fields_sql = []
            values = []
            
            # SECURITY: Only process fields that are in the whitelist
            for field in updated_fields:
                if field not in ALLOWED_DEVICE_LIST_UPDATE_FIELDS:
                    logger.warning(f"Attempted to update disallowed field: {field} for device {device_id}")
                    continue
                    
                value = getattr(device, field)
                if field in ['weather_device_config', 'tilt_configs'] and value is not None:
                    # Convert JSON to string for database
                    update_fields_sql.append(f"{field} = %s::jsonb")
                    values.append(json_module.dumps(value))
                elif field in ['installation_date', 'last_performance_test_date']:
                    update_fields_sql.append(f"{field} = %s")
                    values.append(value)
                else:
                    update_fields_sql.append(f"{field} = %s")
                    values.append(value)
            
            if update_fields_sql:
                values.append(device_id)
                # SECURITY: Field names are validated against whitelist, values are parameterized
                update_query = f"""
                    UPDATE device_list 
                    SET {', '.join(update_fields_sql)}
                    WHERE device_id = %s
                """
                cursor.execute(update_query, values)
        
        logger.info(f"Updated device {device_id} PV config: {', '.join(updated_fields)} by user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Device {device_id} updated successfully',
            'updated_fields': updated_fields
        })
        
    except device_list.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Device not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_update_device_pv_config: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["POST"])
@cors_allow_same_site
def api_bulk_assign_modules(request):
    """
    Bulk assign PV module configuration to multiple devices
    
    POST data (JSON):
        - device_ids: Array of device IDs
        - config: Configuration object with fields to apply to all devices
    
    Returns:
        JSON with summary of updates
    """
    try:
        data = json.loads(request.body)
        
        device_ids = data.get('device_ids', [])
        config = data.get('config', {})
        
        if not device_ids:
            return JsonResponse({
                'success': False,
                'error': 'No devices selected'
            }, status=400)
        
        if not config:
            return JsonResponse({
                'success': False,
                'error': 'No configuration provided'
            }, status=400)
        
        # Validate module exists if provided
        if 'module_datasheet_id' in config and config['module_datasheet_id']:
            if not PVModuleDatasheet.objects.filter(id=config['module_datasheet_id']).exists():
                return JsonResponse({
                    'success': False,
                    'error': f"Module datasheet ID {config['module_datasheet_id']} not found"
                }, status=400)
        
        # Update devices in transaction
        updated_count = 0
        failed = []
        
        with transaction.atomic():
            for device_id in device_ids:
                try:
                    device = device_list.objects.get(device_id=device_id)
                    
                    # Apply configuration
                    if 'module_datasheet_id' in config:
                        device.module_datasheet_id = config['module_datasheet_id']
                    if 'modules_in_series' in config:
                        device.modules_in_series = config['modules_in_series']
                    if 'installation_date' in config:
                        device.installation_date = config['installation_date']
                    if 'tilt_angle' in config:
                        device.tilt_angle = config['tilt_angle']
                    if 'azimuth_angle' in config:
                        device.azimuth_angle = config['azimuth_angle']
                    if 'mounting_type' in config:
                        device.mounting_type = config['mounting_type']
                    if 'expected_soiling_loss' in config:
                        device.expected_soiling_loss = config['expected_soiling_loss']
                    if 'shading_factor' in config:
                        device.shading_factor = config['shading_factor']
                    
                    device.save()
                    updated_count += 1
                    
                except device_list.DoesNotExist:
                    failed.append({'device_id': device_id, 'error': 'Device not found'})
                except Exception as e:
                    failed.append({'device_id': device_id, 'error': str(e)})
        
        logger.info(
            f"Bulk assign PV config to {updated_count} devices by user {request.user.username}"
        )
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'failed_count': len(failed),
            'failed_devices': failed,
            'message': f'Successfully updated {updated_count} of {len(device_ids)} devices'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_bulk_assign_modules: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["POST"])
@cors_allow_same_site
def api_import_device_pv_config(request):
    """
    Import device PV configurations from CSV
    
    POST data (multipart/form-data):
        - file: CSV file
    
    CSV format:
        device_id,module_model,modules_in_series,installation_date,tilt_angle,azimuth_angle,...
    
    Returns:
        JSON with import summary
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file uploaded'
            }, status=400)
        
        csv_file = request.FILES['file']
        
        # Read CSV
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        updated_count = 0
        skipped_count = 0
        errors = []
        
        # Build module lookup cache
        module_lookup = {}
        for module in PVModuleDatasheet.objects.all():
            module_lookup[module.module_model] = module.id
        
        for row_num, row in enumerate(reader, start=2):
            try:
                device_id = row.get('device_id', '').strip()
                
                if not device_id:
                    errors.append(f"Row {row_num}: Missing device_id")
                    continue
                
                # Get device
                try:
                    device = device_list.objects.get(device_id=device_id)
                except device_list.DoesNotExist:
                    errors.append(f"Row {row_num}: Device {device_id} not found")
                    continue
                
                # Get module ID from module_model name
                module_model = row.get('module_model', '').strip()
                if module_model:
                    if module_model not in module_lookup:
                        errors.append(f"Row {row_num}: Module '{module_model}' not found")
                        continue
                    device.module_datasheet_id = module_lookup[module_model]
                
                # Update configuration
                if row.get('modules_in_series'):
                    device.modules_in_series = int(row['modules_in_series'])
                
                if row.get('installation_date'):
                    device.installation_date = row['installation_date']
                
                if row.get('tilt_angle'):
                    device.tilt_angle = float(row['tilt_angle'])
                
                if row.get('azimuth_angle'):
                    device.azimuth_angle = float(row['azimuth_angle'])
                
                if row.get('mounting_type'):
                    device.mounting_type = row['mounting_type']
                
                if row.get('expected_soiling_loss'):
                    device.expected_soiling_loss = float(row['expected_soiling_loss'])
                
                if row.get('shading_factor'):
                    device.shading_factor = float(row['shading_factor'])
                
                if row.get('measured_degradation_rate'):
                    device.measured_degradation_rate = float(row['measured_degradation_rate'])
                
                if row.get('operational_notes'):
                    device.operational_notes = row['operational_notes']
                
                device.save()
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num} ({row.get('device_id', 'unknown')}): {str(e)}")
                continue
        
        logger.info(
            f"Device PV config CSV import by {request.user.username}: "
            f"{updated_count} updated, {skipped_count} skipped, {len(errors)} errors"
        )
        
        return JsonResponse({
            'success': True,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors,
            'total_processed': updated_count + skipped_count + len(errors)
        })
        
    except Exception as e:
        logger.error(f"Error in api_import_device_pv_config: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_export_device_pv_config(request):
    """
    Export device PV configurations to CSV
    
    Query params:
        - asset_code: Filter by asset (optional)
    
    Returns:
        CSV file with device PV configurations
    """
    try:
        # Query devices
        devices = device_list.objects.filter(
            device_type__icontains='string'
        ).select_related('module_datasheet')
        
        asset_code = request.GET.get('asset_code')
        if asset_code:
            devices = devices.filter(parent_code=asset_code)
            filename = f'device_pv_config_{asset_code}.csv'
        else:
            filename = 'device_pv_config_all.csv'
        
        # Create response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'device_id', 'device_name', 'parent_code',
            'module_model', 'modules_in_series',
            'installation_date', 'tilt_angle', 'azimuth_angle',
            'mounting_type', 'expected_soiling_loss', 'shading_factor',
            'measured_degradation_rate', 'last_performance_test_date',
            'operational_notes', 'string_rated_power'
        ])
        
        # Write data
        for device in devices:
            writer.writerow([
                device.device_id,
                device.device_name,
                device.parent_code,
                device.module_datasheet.module_model if device.module_datasheet else '',
                device.modules_in_series or '',
                device.installation_date or '',
                device.tilt_angle or '',
                device.azimuth_angle or '',
                device.mounting_type or '',
                device.expected_soiling_loss or '',
                device.shading_factor or '',
                device.measured_degradation_rate or '',
                device.last_performance_test_date or '',
                device.operational_notes or '',
                device.string_rated_power or ''
            ])
        
        logger.info(f"Exported {devices.count()} device PV configs to CSV by user {request.user.username}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in api_export_device_pv_config: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@feature_required('site_onboarding')
@require_http_methods(["GET"])
@cors_allow_same_site
def api_download_device_pv_config_template(request):
    """
    Download CSV template for device PV configuration import
    
    Returns:
        CSV file with headers and sample data
    """
    try:
        import csv
        from django.http import HttpResponse
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="device_pv_config_template.csv"'
        
        writer = csv.writer(response)
        
        # Headers matching DevicePVConfig interface
        headers = [
            'device_id', 'module_datasheet_id', 'modules_in_series',
            'installation_date', 'tilt_angle', 'azimuth_angle', 'mounting_type',
            'expected_soiling_loss', 'shading_factor',
            'measured_degradation_rate', 'last_performance_test_date',
            'operational_notes', 'power_model_id'
        ]
        writer.writerow(headers)
        
        # Sample data row
        sample_data = [
            'DEV_001',  # device_id
            '1',  # module_datasheet_id (use ID from PV Module Library)
            '24',  # modules_in_series
            '2023-01-15',  # installation_date
            '30.0',  # tilt_angle (degrees)
            '180.0',  # azimuth_angle (degrees, 180 = South)
            'Fixed',  # mounting_type (Fixed, Single-Axis Tracker, Dual-Axis Tracker, Ground Mount, Rooftop)
            '2.0',  # expected_soiling_loss (%)
            '0.5',  # shading_factor (%)
            '0.5',  # measured_degradation_rate (%/year)
            '2023-06-15',  # last_performance_test_date
            'Sample notes about this device configuration',  # operational_notes
            '1'  # power_model_id (use ID from Power Model Registry, optional)
        ]
        writer.writerow(sample_data)
        
        logger.info(f"Device PV config template downloaded by user {request.user.username}")
        return response
        
    except Exception as e:
        logger.error(f"Error in api_download_device_pv_config_template: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==========================================
# POWER MODEL APIs (Plugin Architecture)
# ==========================================

@login_required
@require_http_methods(["GET"])
@cors_allow_same_site
def api_list_power_models(request):
    """
    List all available power calculation models.

    Primary source of truth is the in-memory model_registry (main.calculations.models),
    but this view is resilient: if registry import or list_models() fails, it falls
    back to PowerModelRegistry rows in the database.
    """
    try:
        models: list[dict] = []

        try:
            from main.calculations.models import model_registry

            models_raw = model_registry.list_models()

            # Sync models from registry to PowerModelRegistry table
            for model_info in models_raw:
                model_code = model_info.get('code', '')
                if not model_code:
                    continue

                try:
                    db_model = PowerModelRegistry.objects.get(model_code=model_code)
                    # Update if metadata changed
                    if (
                        db_model.model_name != model_info.get('name', '')
                        or db_model.model_version != model_info.get('version', '')
                        or db_model.model_type != model_info.get('type', '')
                    ):
                        db_model.model_name = model_info.get('name', '')
                        db_model.model_version = model_info.get('version', '')
                        db_model.model_type = model_info.get('type', '')
                        db_model.is_default = model_info.get('is_default', False)
                        db_model.save()
                        logger.info("Updated PowerModelRegistry entry for %s", model_code)
                except PowerModelRegistry.DoesNotExist:
                    db_model = PowerModelRegistry.objects.create(
                        model_code=model_code,
                        model_name=model_info.get('name', ''),
                        model_version=model_info.get('version', ''),
                        model_type=model_info.get('type', ''),
                        is_default=model_info.get('is_default', False),
                        is_active=True,
                    )
                    logger.info(
                        "Auto-created PowerModelRegistry entry for %s (ID: %s)",
                        model_code,
                        db_model.id,
                    )

                if db_model.is_active:
                    models.append(
                        {
                            "id": db_model.id,
                            "code": model_code,
                            "name": db_model.model_name,
                            "version": db_model.model_version,
                            "type": db_model.model_type,
                            "is_default": db_model.is_default,
                            "requires_weather_data": model_info.get("requires_weather_data", True),
                            "requires_module_datasheet": model_info.get(
                                "requires_module_datasheet", True
                            ),
                            "requires_historical_data": model_info.get(
                                "requires_historical_data", False
                            ),
                            "supports_degradation": model_info.get("supports_degradation", True),
                            "supports_soiling": model_info.get("supports_soiling", True),
                            "supports_bifacial": model_info.get("supports_bifacial", False),
                            "supports_shading": model_info.get("supports_shading", True),
                        }
                    )
        except Exception as registry_exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Falling back to PowerModelRegistry only in api_list_power_models: %s",
                registry_exc,
            )

        # If for some reason registry produced nothing, fall back to DB rows only
        if not models:
            for db_model in PowerModelRegistry.objects.filter(is_active=True).order_by(
                "model_code"
            ):
                models.append(
                    {
                        "id": db_model.id,
                        "code": db_model.model_code,
                        "name": db_model.model_name,
                        "version": db_model.model_version,
                        "type": db_model.model_type,
                        "is_default": db_model.is_default,
                        # Conservative defaults when we don't have registry metadata
                        "requires_weather_data": True,
                        "requires_module_datasheet": True,
                        "requires_historical_data": False,
                        "supports_degradation": True,
                        "supports_soiling": True,
                        "supports_bifacial": False,
                        "supports_shading": True,
                    }
                )

        return JsonResponse({"success": True, "count": len(models), "models": models})

    except Exception as e:
        logger.error("Error in api_list_power_models: %s", e, exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


