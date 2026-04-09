"""
Site onboarding views: core tables (assets, devices, budgets, etc.).

Data-collection adapter endpoints (Fusion Solar, LaplaceID, adapter accounts,
AssetAdapterConfig CRUD) live in ``main.views.site_onboarding`` and are merged
into ``main.views`` via ``views/__init__.py``.
"""
import csv
import io
import json
import logging
import math
import pandas as pd
from datetime import timezone, datetime

logger = logging.getLogger(__name__)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone as django_timezone
from django.db import models
from django.forms.models import model_to_dict

from ..models import (
    AssetList, device_list, device_mapping, budget_values, ic_budget, assets_contracts, DataImportLog
)
from .shared.validators import validate_csv_structure
from .shared.utilities import ensure_unicode_string
from .shared.decorators import superuser_required
from accounts.decorators import role_required

# Site Onboarding Views - Admin Only
@role_required(allowed_roles=['admin'])
@login_required
def site_onboarding_view(request):
    """Site Onboarding main page for managing asset_list, device_list, and device_mapping"""
    # Check if React version is enabled via waffle flag
    from waffle import flag_is_active
    use_react = flag_is_active(request, 'react_site_onboarding')
    
    if use_react:
        return render(request, 'main/site_onboarding_react.html')
    
    return render(request, 'main/site_onboarding.html')


@role_required(allowed_roles=['admin'])
@login_required
def site_onboarding_wizard_view(request):
    """Single-site onboarding wizard page. Admin only; no delete actions."""
    from waffle import flag_is_active
    use_react = flag_is_active(request, 'react_site_onboarding')
    if use_react:
        return render(request, 'main/site_onboarding_wizard.html')
    return render(request, 'main/site_onboarding.html')


@login_required
@role_required(allowed_roles=['admin'])
def api_site_onboarding_debug(request):
    """Debug endpoint for site onboarding issues"""
    try:
        debug_info = {
            'user_authenticated': request.user.is_authenticated,
            'user_username': request.user.username if request.user.is_authenticated else 'Anonymous',
            'user_is_admin': request.user.is_staff if request.user.is_authenticated else False,
            'user_groups': [group.name for group in request.user.groups.all()] if request.user.is_authenticated else [],
            'request_method': request.method,
            'request_path': request.path,
            'request_params': dict(request.GET),
        }
        
        # Test database connection
        try:
            asset_count = AssetList.objects.count()
            debug_info['database_connection'] = 'OK'
            debug_info['asset_list_count'] = asset_count
        except Exception as db_error:
            debug_info['database_connection'] = 'ERROR'
            debug_info['database_error'] = str(db_error)
        
        return JsonResponse({
            'status': 'site_debug_info',
            'debug': debug_info,
            'timestamp': django_timezone.now().isoformat()
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'debug_error',
            'error': str(e),
            'timestamp': django_timezone.now().isoformat()
        }, status=500)


@login_required
@role_required(allowed_roles=['admin'])
def api_budget_values_debug(request):
    """Debug endpoint specifically for budget_values upload issues"""
    try:
        debug_info = {
            'timestamp': django_timezone.now().isoformat(),
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
        }
        
        # Test database connection and table structure
        try:
            count = budget_values.objects.count()
            debug_info['database_status'] = 'OK'
            debug_info['budget_values_count'] = count
            
            # Get table structure
            model_fields = [field.name for field in budget_values._meta.fields]
            debug_info['model_fields'] = model_fields
            
            if count > 0:
                sample = budget_values.objects.first()
                debug_info['sample_record'] = {
                    'asset_code': sample.asset_code,
                    'month_str': sample.month_str,
                    'bd_production': float(sample.bd_production) if sample.bd_production else None
                }
            
        except Exception as db_error:
            debug_info['database_status'] = 'ERROR'
            debug_info['database_error'] = str(db_error)
            import traceback
            debug_info['database_traceback'] = traceback.format_exc()
        
        # Test validation functions
        try:
            test_data = {
                'asset_code': ['TEST001'],
                'month_str': ['JAN'],
                'bd_production': [100.0],
                'bd_ghi': [5.0],
                'bd_gti': [6.0]
            }
            test_df = pd.DataFrame(test_data)
            
            csv_validation = validate_csv_structure(test_df, 'budget_values')
            
            debug_info['validation_functions'] = {
                'csv_validation': {
                    'valid': csv_validation[0],
                    'error': csv_validation[1],
                    'missing_fields': csv_validation[2],
                    'extra_fields': csv_validation[3]
                }
            }
            
        except Exception as validation_error:
            debug_info['validation_functions'] = 'ERROR'
            debug_info['validation_error'] = str(validation_error)
            import traceback
            debug_info['validation_traceback'] = traceback.format_exc()
        
        return JsonResponse({
            'status': 'budget_debug_info',
            'debug': debug_info
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'budget_debug_error',
            'error': str(e),
            'timestamp': django_timezone.now().isoformat()
        }, status=500)


# Placeholder for all site onboarding API endpoints
# These would include CRUD operations for:
# - Asset List
# - Device List  
# - Device Mapping
# - Budget Values
# - IC Budget

@role_required(allowed_roles=['admin'])
@login_required
def api_asset_list_data(request):
    """API endpoint to get asset list data with pagination"""
    try:
        # Debug logging for production troubleshooting
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Asset list API called by user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
        
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        
        logger.info(f"Asset list query params: page={page}, page_size={page_size}, search='{search}'")
        
        try:
            assets = AssetList.objects.all()
            logger.info(f"AssetList query successful, found {assets.count()} total assets")
        except Exception as db_error:
            logger.error(f"Database error in AssetList query: {str(db_error)}")
            return JsonResponse({
                'error': 'Database connection error',
                'details': str(db_error),
                'user': request.user.username if request.user.is_authenticated else 'Anonymous'
            }, status=500)
        
        if search:
            assets = assets.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(asset_name__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(portfolio__icontains=search)
            )
        
        total_count = assets.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        assets_page = assets[start:end]
        
        data = []
        for asset in assets_page:
            try:
                asset_data = {
                    'asset_code': asset.asset_code,
                    'asset_name': asset.asset_name,
                    'provider_asset_id': getattr(asset, 'provider_asset_id', '') or '',
                    'capacity': float(asset.capacity) if asset.capacity else 0,
                    'address': asset.address,
                    'country': asset.country,
                    'latitude': float(asset.latitude) if asset.latitude else 0,
                    'longitude': float(asset.longitude) if asset.longitude else 0,
                    'contact_person': asset.contact_person,
                    'contact_method': asset.contact_method,
                    'grid_connection_date': asset.grid_connection_date.isoformat() if asset.grid_connection_date else '',
                    'asset_number': asset.asset_number,
                    'customer_name': getattr(asset, 'customer_name', '') or '',
                    'portfolio': getattr(asset, 'portfolio', ''),
                    'timezone': asset.timezone,
                    'asset_name_oem': getattr(asset, 'asset_name_oem', ''),
                    'cod': asset.cod.isoformat() if getattr(asset, 'cod', None) else '',
                    'operational_cod': asset.operational_cod.isoformat() if getattr(asset, 'operational_cod', None) else '',
                    'y1_degradation': float(asset.y1_degradation) if getattr(asset, 'y1_degradation', None) else None,
                    'anual_degradation': float(asset.anual_degradation) if getattr(asset, 'anual_degradation', None) else None,
                    'api_name': getattr(asset, 'api_name', '') or '',
                    'api_key': getattr(asset, 'api_key', '') or '',
                    'tilt_configs': getattr(asset, 'tilt_configs', None),
                    'altitude_m': float(asset.altitude_m) if getattr(asset, 'altitude_m', None) is not None else None,
                    'albedo': float(asset.albedo) if getattr(asset, 'albedo', None) is not None else None,
                    'pv_syst_pr': float(asset.pv_syst_pr) if getattr(asset, 'pv_syst_pr', None) is not None else None,
                    'satellite_irradiance_source_asset_code': getattr(asset, 'satellite_irradiance_source_asset_code', '') or '',
                }
                data.append(asset_data)
            except Exception as asset_error:
                logger.error(f"Error processing asset {asset.asset_code}: {str(asset_error)}")
                # Add minimal asset data to prevent complete failure
                data.append({
                    'asset_code': asset.asset_code,
                    'asset_name': asset.asset_name,
                    'capacity': 0,
                    'address': getattr(asset, 'address', ''),
                    'country': getattr(asset, 'country', ''),
                    'latitude': 0,
                    'longitude': 0,
                    'contact_person': getattr(asset, 'contact_person', ''),
                    'contact_method': getattr(asset, 'contact_method', ''),
                    'grid_connection_date': '',
                    'asset_number': getattr(asset, 'asset_number', ''),
                    'customer_name': getattr(asset, 'customer_name', '') or '',
                    'portfolio': '',
                    'timezone': getattr(asset, 'timezone', ''),
                    'asset_name_oem': '',
                    'cod': '',
                    'operational_cod': '',
                    'y1_degradation': None,
                    'anual_degradation': None,
                    'api_name': '',
                    'api_key': '',
                    'tilt_configs': None,
                    'altitude_m': None,
                    'albedo': None,
                    'pv_syst_pr': None,
                    'satellite_irradiance_source_asset_code': '',
                })
        
        logger.info(f"Asset list API returning {len(data)} assets for page {page}")
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_asset_list_data: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e),
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
            'endpoint': 'api_asset_list_data'
        }, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_device_list_data(request):
    """API endpoint to get device list data with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        parent_code_filter = request.GET.get('parent_code', '').strip()
        parent_code_filters = [pc.strip() for pc in parent_code_filter.split(',') if pc.strip()]
        
        devices = device_list.objects.all()
        
        # Apply parent_code filter
        if parent_code_filters:
            devices = devices.filter(parent_code__in=parent_code_filters)
        
        # Apply search filter
        if search:
            devices = devices.filter(
                models.Q(device_id__icontains=search) |
                models.Q(device_name__icontains=search) |
                models.Q(device_code__icontains=search) |
                models.Q(device_type__icontains=search) |
                models.Q(parent_code__icontains=search) |
                models.Q(country__icontains=search)
            )
        
        total_count = devices.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        devices_page = devices[start:end]
        
        data = []
        for device in devices_page:
            data.append({
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_code': device.device_code,
                'device_type_id': device.device_type_id,
                'device_serial': device.device_serial,
                'device_model': device.device_model,
                'device_make': device.device_make,
                'latitude': float(device.latitude) if device.latitude else 0,
                'longitude': float(device.longitude) if device.longitude else 0,
                'optimizer_no': device.optimizer_no,
                'parent_code': device.parent_code,
                'device_type': device.device_type,
                'software_version': device.software_version,
                'country': device.country,
                'string_no': device.string_no,
                'connected_strings': device.connected_strings,
                'device_sub_group': device.device_sub_group,
                'dc_cap': float(device.dc_cap) if device.dc_cap else 0,
                'device_source': device.device_source,
                'ac_capacity': float(device.ac_capacity) if device.ac_capacity else None,
                'equipment_warranty_start_date': device.equipment_warranty_start_date.isoformat() if device.equipment_warranty_start_date else None,
                'equipment_warranty_expire_date': device.equipment_warranty_expire_date.isoformat() if device.equipment_warranty_expire_date else None,
                'epc_warranty_start_date': device.epc_warranty_start_date.isoformat() if device.epc_warranty_start_date else None,
                'epc_warranty_expire_date': device.epc_warranty_expire_date.isoformat() if device.epc_warranty_expire_date else None,
                'calibration_frequency': device.calibration_frequency or '',
                'pm_frequency': device.pm_frequency or '',
                'visual_inspection_frequency': device.visual_inspection_frequency or '',
                'bess_capacity': float(device.bess_capacity) if device.bess_capacity else None,
                'yom': device.yom or '',
                'nomenclature': device.nomenclature or '',
                'location': device.location or '',
                # PV Module Configuration Fields (Added in Phase 4)
                'module_datasheet_id': device.module_datasheet_id,
                'modules_in_series': device.modules_in_series,
                'installation_date': device.installation_date.isoformat() if device.installation_date else None,
                'tilt_angle': float(device.tilt_angle) if device.tilt_angle else None,
                'azimuth_angle': float(device.azimuth_angle) if device.azimuth_angle else None,
                'mounting_type': device.mounting_type or None,
                'expected_soiling_loss': float(device.expected_soiling_loss) if device.expected_soiling_loss is not None else None,
                'shading_factor': float(device.shading_factor) if device.shading_factor is not None else None,
                'measured_degradation_rate': float(device.measured_degradation_rate) if device.measured_degradation_rate else None,
                'last_performance_test_date': device.last_performance_test_date.isoformat() if device.last_performance_test_date else None,
                'operational_notes': device.operational_notes or None,
                'power_model_id': device.power_model_id,
                'power_model_config': device.power_model_config,
                'model_fallback_enabled': device.model_fallback_enabled if device.model_fallback_enabled is not None else None,
                'weather_device_config': device.weather_device_config,
                'tilt_configs': getattr(device, 'tilt_configs', None),
            })
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_device_list_including_gii(request):
    """
    Return device list for an asset including synthetic GII device_ids (8.7).
    GET ?asset_code=XXX — devices with parent_code=XXX plus one entry per asset tilt_config:
    device_id = {asset_code}_gii_{tilt}_{azimuth}, so GII devices are visible downstream.
    """
    try:
        asset_code = (request.GET.get('asset_code') or '').strip()
        if not asset_code:
            return JsonResponse({'error': 'asset_code is required'}, status=400)
        devices_qs = device_list.objects.filter(parent_code=asset_code).order_by('device_id')
        data = []
        for device in devices_qs:
            data.append({
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_code': getattr(device, 'device_code', ''),
                'device_type_id': getattr(device, 'device_type_id', ''),
                'parent_code': device.parent_code,
                'device_type': device.device_type,
                'country': device.country,
                'device_source': getattr(device, 'device_source', '') or '',
            })
        existing_ids = {d['device_id'] for d in data}
        try:
            asset = AssetList.objects.filter(asset_code=asset_code).first()
            if asset and getattr(asset, 'tilt_configs', None) and isinstance(asset.tilt_configs, list):
                from loss_analytics.pipeline.transposition import gii_device_id
                country = (getattr(asset, 'country', None) or '').strip() or '—'
                for cfg in asset.tilt_configs:
                    if not isinstance(cfg, dict):
                        continue
                    try:
                        tilt_deg = float(cfg.get('tilt_deg', 0))
                        azimuth_deg = float(cfg.get('azimuth_deg', 0))
                    except (TypeError, ValueError):
                        continue
                    dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
                    if dev_id not in existing_ids:
                        existing_ids.add(dev_id)
                        data.append({
                            'device_id': dev_id,
                            'device_name': f"GII {int(round(tilt_deg))}° {int(round(azimuth_deg))}°",
                            'device_code': dev_id,
                            'device_type_id': 'gii',
                            'parent_code': asset_code,
                            'device_type': 'GII',
                            'country': country,
                            'device_source': 'gii',
                        })
        except Exception as e:
            logger.warning("api_device_list_including_gii: failed to add GII placeholders: %s", e)
        return JsonResponse({'data': data, 'total': len(data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_device_mapping_data(request):
    """API endpoint to get device mapping data with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        asset_code_filter = request.GET.get('asset_code', '').strip()
        
        # Check if device_mapping table exists
        try:
            mappings = device_mapping.objects.all()
        except Exception as db_error:
            print(f"Database error accessing device_mapping: {str(db_error)}")
            # Return empty result if table doesn't exist
            return JsonResponse({
                'data': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'warning': 'Device mapping table not found. Please ensure the table exists in the database.'
            })
        
        # Apply asset_code filter (case-insensitive for better usability)
        if asset_code_filter:
            mappings = mappings.filter(asset_code__iexact=asset_code_filter)
        
        # Apply search filter
        if search:
            mappings = mappings.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(device_type__icontains=search) |
                models.Q(oem_tag__icontains=search) |
                models.Q(discription__icontains=search) |
                models.Q(metric__icontains=search)
            )
        
        total_count = mappings.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        mappings_page = mappings[start:end]
        
        data = []
        for mapping in mappings_page:
            # Try to get asset details if asset_code is available
            asset_details = {}
            if mapping.asset_code:
                try:
                    asset = AssetList.objects.get(asset_code=mapping.asset_code)
                    asset_details = {
                        'asset_name': asset.asset_name,
                        'asset_number': asset.asset_number,
                        'country': asset.country,
                        'portfolio': asset.portfolio,
                    }
                except AssetList.DoesNotExist:
                    pass
            
            data.append({
                'id': mapping.id,
                'asset_code': mapping.asset_code,
                'device_type': mapping.device_type,
                'oem_tag': mapping.oem_tag,
                'description': mapping.description,  # Use the property for proper spelling
                'data_type': mapping.data_type,
                'units': mapping.units,
                'metric': mapping.metric,
                'fault_code': mapping.fault_code or '',
                'module_no': mapping.module_no or '',
                'default_value': mapping.default_value or '',
                # Include asset details for better UX
                **asset_details,
            })
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        print(f"Error in api_device_mapping_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_device_operating_state_data(request):
    """API endpoint to get device operating state mappings with pagination and filters."""
    try:
        from data_collection.models import DeviceOperatingState

        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        adapter_id_filter = request.GET.get('adapter_id', '').strip()
        device_type_filter = request.GET.get('device_type', '').strip()

        qs = DeviceOperatingState.objects.all().order_by('adapter_id', 'device_type', 'state_value')
        if adapter_id_filter:
            qs = qs.filter(adapter_id=adapter_id_filter)
        if device_type_filter:
            qs = qs.filter(device_type=device_type_filter)
        if search:
            qs = qs.filter(
                models.Q(adapter_id__icontains=search)
                | models.Q(device_type__icontains=search)
                | models.Q(state_value__icontains=search)
                | models.Q(oem_state_label__icontains=search)
                | models.Q(internal_state__icontains=search)
            )

        total_count = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]

        data = []
        for row in page_qs:
            data.append(
                {
                    "id": row.id,
                    "adapter_id": row.adapter_id,
                    "device_type": row.device_type,
                    "state_value": row.state_value,
                    "oem_state_label": row.oem_state_label,
                    "internal_state": row.internal_state,
                    "is_normal": bool(row.is_normal),
                    "fault_code": row.fault_code or "",
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                    "updated_at": row.updated_at.isoformat() if row.updated_at else "",
                }
            )

        return JsonResponse(
            {
                "data": data,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": math.ceil(total_count / page_size) if total_count else 0,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_budget_values_data(request):
    """API endpoint to get budget values data with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        asset_code_filter = request.GET.get('asset_code', '').strip()
        
        print(f"Budget values API called - page: {page}, page_size: {page_size}, search: '{search}', asset_code: '{asset_code_filter}'")
        
        budgets = budget_values.objects.all().order_by('asset_code', 'month_str')
        print(f"Total budget records found: {budgets.count()}")
        
        # Apply asset_code filter
        if asset_code_filter:
            budgets = budgets.filter(asset_code=asset_code_filter)
        
        # Apply search filter
        if search:
            budgets = budgets.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(asset_number__icontains=search) |
                models.Q(month_str__icontains=search)
            )
        
        total_count = budgets.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        budgets_page = budgets[start:end]
        
        data = []
        for budget in budgets_page:
            data.append({
                'id': budget.id,
                'asset_number': budget.asset_number,
                'asset_code': budget.asset_code,
                'month_str': budget.month_str,
                'month_date': budget.month_date.isoformat() if budget.month_date else '',
                'bd_production': float(budget.bd_production) if budget.bd_production else 0,
                'bd_ghi': float(budget.bd_ghi) if budget.bd_ghi else 0,
                'bd_gti': float(budget.bd_gti) if budget.bd_gti else 0,
            })
        
        print(f"Returning {len(data)} budget records")
        print(f"Sample data: {data[:2] if data else 'No data'}")
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        print(f"Error in api_budget_values_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_create_asset_list(request):
    """API endpoint to create new asset list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields (after normalizing, so we reject empty lists etc.)
            def _req(field):
                v = data.get(field)
                if v is None or v == '':
                    return False
                if isinstance(v, (list, tuple)):
                    return len(v) > 0 and v[0] is not None and str(v[0]).strip() != ''
                return str(v).strip() != ''
            for field in ['asset_code', 'asset_name', 'country', 'portfolio', 'timezone']:
                if not _req(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)

            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle datetime formatting
                def parse_datetime(date_str):
                    if date_str:
                        try:
                            from datetime import datetime
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            return None
                    return None
                
                grid_connection_date = parse_datetime(data.get('grid_connection_date'))
                cod_date = parse_datetime(data.get('cod'))
                operational_cod_date = parse_datetime(data.get('operational_cod'))
                
                # tilt_configs: store as JSON string for JSONB column
                tilt_configs_val = data.get('tilt_configs')
                if tilt_configs_val is not None and not isinstance(tilt_configs_val, str):
                    tilt_configs_val = json.dumps(tilt_configs_val) if tilt_configs_val else None

                altitude_m_val = _asset_num(data.get('altitude_m'))
                albedo_val = _asset_num(data.get('albedo'))
                pv_syst_pr_val = _asset_num(data.get('pv_syst_pr'))

                # Normalize string fields (avoid list index errors and .strip() on numbers)
                asset_code = _asset_str(data.get('asset_code'))
                asset_name = _asset_str(data.get('asset_name'))
                provider_asset_id = _asset_str(data.get('provider_asset_id'), default=None) or None
                capacity_val = _asset_num(data.get('capacity'))
                address = _asset_str(data.get('address'))
                country = _asset_str(data.get('country'))
                latitude_val = _asset_num(data.get('latitude'))
                longitude_val = _asset_num(data.get('longitude'))
                contact_person = _asset_str(data.get('contact_person'))
                contact_method = _asset_str(data.get('contact_method'))
                asset_number = _asset_str(data.get('asset_number'))
                customer_name = _asset_str(data.get('customer_name'))
                timezone_str = _asset_str(data.get('timezone'))
                asset_name_oem = _asset_str(data.get('asset_name_oem'))
                portfolio = _asset_str(data.get('portfolio'))
                y1_val = _asset_num(data.get('y1_degradation'))
                anual_val = _asset_num(data.get('anual_degradation'))
                api_name_str = _asset_str(data.get('api_name'))
                api_key_str = _asset_str(data.get('api_key'))
                satellite_src = _asset_str(data.get('satellite_irradiance_source_asset_code'), default=None) or None

                # Insert into asset_list table (provider_asset_id for Fusion Solar / OEM plant ID)
                # Original SQL had 27 placeholders (22+%s::jsonb+4) but we pass 26 params -> IndexError. Use 26 placeholders.
                cols = [
                    'asset_code', 'asset_name', 'provider_asset_id', 'capacity', 'address', 'country',
                    'latitude', 'longitude', 'contact_person', 'contact_method',
                    'grid_connection_date', 'asset_number', 'timezone', 'asset_name_oem',
                    'customer_name',
                    'cod', 'operational_cod', 'portfolio', 'y1_degradation', 'anual_degradation',
                    'api_name', 'api_key', 'tilt_configs', 'altitude_m', 'albedo', 'pv_syst_pr',
                    'satellite_irradiance_source_asset_code',
                ]
                params = [
                    asset_code,
                    asset_name,
                    provider_asset_id,
                    capacity_val,
                    address,
                    country,
                    latitude_val,
                    longitude_val,
                    contact_person,
                    contact_method,
                    grid_connection_date,
                    asset_number,
                    timezone_str,
                    asset_name_oem,
                    customer_name,
                    cod_date,
                    operational_cod_date,
                    portfolio,
                    y1_val,
                    anual_val,
                    api_name_str,
                    api_key_str,
                    tilt_configs_val,
                    altitude_m_val,
                    albedo_val,
                    pv_syst_pr_val,
                    satellite_src,
                ]
                # 26 placeholders to match 26 params: 21 + %s::jsonb + 4 (original had 22 in first block -> one extra)
                ph = ['%s'] * 22 + ['%s::jsonb'] + ['%s'] * 4
                cursor.execute(
                    "INSERT INTO asset_list (" + ', '.join(cols) + ") VALUES (" + ', '.join(ph) + ")",
                    params,
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Asset created successfully!'
            })
            
        except Exception as e:
            logger.exception('api_create_asset_list failed')
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


def _asset_str(val, default=''):
    """Coerce to string for DB: list/tuple -> first element; then str and strip. Avoids .strip() on numbers and list index errors."""
    if val is None:
        return default
    if isinstance(val, (list, tuple)):
        val = val[0] if val else default
    if val is None or val == '':
        return default
    return str(val).strip() or default


def _asset_num(val):
    """Coerce to float for DB; if list/tuple take first element. Returns None for empty/invalid."""
    if val is None or val == '':
        return None
    if isinstance(val, (list, tuple)):
        val = val[0] if val else None
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_update_asset_list(request):
    """API endpoint to update asset list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            asset_code = _asset_str(data.get('asset_code'))

            if not asset_code:
                return JsonResponse({'error': 'Asset code is required'}, status=400)

            # Use raw SQL to update unmanaged table
            from django.db import connection

            with connection.cursor() as cursor:
                # Handle datetime formatting
                def parse_datetime(date_str):
                    if date_str:
                        try:
                            from datetime import datetime
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            return None
                    return None

                grid_connection_date = parse_datetime(data.get('grid_connection_date'))
                cod_date = parse_datetime(data.get('cod'))
                operational_cod_date = parse_datetime(data.get('operational_cod'))

                # Build dynamic update query based on provided fields
                # SECURITY: Whitelist of allowed field names to prevent SQL injection
                ALLOWED_ASSET_FIELDS = {
                    'asset_name', 'provider_asset_id', 'capacity', 'address', 'country', 'latitude', 'longitude',
                    'contact_person', 'contact_method', 'grid_connection_date', 'asset_number',
                    'timezone', 'asset_name_oem', 'customer_name', 'cod', 'operational_cod', 'portfolio',
                    'y1_degradation', 'anual_degradation', 'api_name', 'api_key',
                    'tilt_configs', 'altitude_m', 'albedo', 'pv_syst_pr',
                    'satellite_irradiance_source_asset_code'
                }
                # tilt_configs: serialize to JSON string for JSONB
                tilt_configs_val = data.get('tilt_configs')
                if tilt_configs_val is not None and not isinstance(tilt_configs_val, str):
                    tilt_configs_val = json.dumps(tilt_configs_val) if tilt_configs_val else None
                altitude_m_val = _asset_num(data.get('altitude_m'))
                albedo_val = _asset_num(data.get('albedo'))
                pv_syst_pr_val = _asset_num(data.get('pv_syst_pr'))

                update_fields = []
                values = []

                field_mappings = {
                    'asset_name': _asset_str(data.get('asset_name')),
                    'provider_asset_id': _asset_str(data.get('provider_asset_id'), default=None) or None,
                    'capacity': _asset_num(data.get('capacity')),
                    'address': _asset_str(data.get('address')),
                    'country': _asset_str(data.get('country')),
                    'latitude': _asset_num(data.get('latitude')),
                    'longitude': _asset_num(data.get('longitude')),
                    'contact_person': _asset_str(data.get('contact_person')),
                    'contact_method': _asset_str(data.get('contact_method')),
                    'grid_connection_date': grid_connection_date,
                    'asset_number': _asset_str(data.get('asset_number')),
                    'timezone': _asset_str(data.get('timezone')),
                    'asset_name_oem': _asset_str(data.get('asset_name_oem')),
                    'customer_name': _asset_str(data.get('customer_name')),
                    'cod': cod_date,
                    'operational_cod': operational_cod_date,
                    'portfolio': _asset_str(data.get('portfolio')),
                    'y1_degradation': _asset_num(data.get('y1_degradation')),
                    'anual_degradation': _asset_num(data.get('anual_degradation')),
                    'api_name': _asset_str(data.get('api_name')),
                    'api_key': _asset_str(data.get('api_key')),
                    'tilt_configs': tilt_configs_val if data.get('tilt_configs') is not None else None,
                    'altitude_m': altitude_m_val if 'altitude_m' in data else None,
                    'albedo': albedo_val if 'albedo' in data else None,
                    'pv_syst_pr': pv_syst_pr_val if 'pv_syst_pr' in data else None,
                    'satellite_irradiance_source_asset_code': _asset_str(data.get('satellite_irradiance_source_asset_code'), default=None) or None,
                }
                
                if 'timezone' in data and not _asset_str(data.get('timezone')):
                    return JsonResponse({'error': 'timezone is required'}, status=400)

                # SECURITY: Only process fields that are in the whitelist and were provided
                for field, value in field_mappings.items():
                    if field in ALLOWED_ASSET_FIELDS and field in data:
                        if field == 'tilt_configs':
                            update_fields.append('tilt_configs = %s::jsonb')
                        else:
                            update_fields.append(f'"{field}" = %s')
                        values.append(value)
                
                if update_fields:
                    values.append(asset_code)  # For WHERE clause
                    # SECURITY: Use parameterized query with validated field names
                    # Field names are now validated against whitelist, values are parameterized
                    query = f"""
                        UPDATE asset_list 
                        SET {', '.join(update_fields)}
                        WHERE asset_code = %s
                    """
                    cursor.execute(query, values)
            
            return JsonResponse({
                'success': True,
                'message': 'Asset updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_delete_asset_list(request, asset_code):
    """API endpoint to delete asset list record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for asset {asset_code}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM asset_list WHERE asset_code = %s", [asset_code])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Asset {asset_code} deleted by superuser {request.user.username} (ID: {request.user.id})")
                
            return JsonResponse({
                'success': True,
                'message': 'Asset deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
def api_get_unique_api_names(request):
    """API endpoint to get unique API names for suggestions"""
    try:
        # Get unique API names that are not null or empty
        unique_names = AssetList.objects.exclude(
            api_name__isnull=True
        ).exclude(
            api_name__exact=''
        ).values_list('api_name', flat=True).distinct().order_by('api_name')
        
        return JsonResponse({
            'success': True,
            'api_names': list(unique_names)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_get_unique_parent_codes(request):
    """API endpoint to get unique parent codes for device filtering"""
    try:
        # Get unique parent codes that are not null or empty
        unique_codes = device_list.objects.exclude(
            parent_code__isnull=True
        ).exclude(
            parent_code__exact=''
        ).values_list('parent_code', flat=True).distinct().order_by('parent_code')
        
        return JsonResponse({
            'success': True,
            'parent_codes': list(unique_codes)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Device List CRUD operations
@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_create_device_list(request):
    """API endpoint to create new device list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['device_id', 'device_name', 'device_type', 'country']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Helper function to parse datetime
            def parse_datetime(date_str):
                if not date_str:
                    return None
                try:
                    from datetime import datetime
                    # Handle datetime-local format (YYYY-MM-DDTHH:MM)
                    if 'T' in date_str:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    return None
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO device_list (
                        device_id, device_name, device_code, device_type_id,
                        device_serial, device_model, device_make, latitude,
                        longitude, optimizer_no, parent_code, device_type,
                        software_version, country, string_no, connected_strings,
                        device_sub_group, dc_cap, device_source, ac_capacity,
                        equipment_warranty_start_date, equipment_warranty_expire_date,
                        epc_warranty_start_date, epc_warranty_expire_date,
                        calibration_frequency, pm_frequency, visual_inspection_frequency,
                        bess_capacity, yom, nomenclature, location,
                        power_model_config, weather_device_config, tilt_configs
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                """, [
                    data.get('device_id'),
                    data.get('device_name'),
                    data.get('device_code', ''),
                    data.get('device_type_id', ''),
                    data.get('device_serial', ''),
                    data.get('device_model', ''),
                    data.get('device_make', ''),
                    float(data.get('latitude', 0)) if data.get('latitude') else 0,
                    float(data.get('longitude', 0)) if data.get('longitude') else 0,
                    int(data.get('optimizer_no', 0)) if data.get('optimizer_no') else 0,
                    data.get('parent_code', ''),
                    data.get('device_type'),
                    data.get('software_version', ''),
                    data.get('country'),
                    data.get('string_no', ''),
                    data.get('connected_strings', ''),
                    data.get('device_sub_group', ''),
                    float(data.get('dc_cap', 0)) if data.get('dc_cap') else None,
                    data.get('device_source', ''),
                    float(data.get('ac_capacity', 0)) if data.get('ac_capacity') else None,
                    parse_datetime(data.get('equipment_warranty_start_date')),
                    parse_datetime(data.get('equipment_warranty_expire_date')),
                    parse_datetime(data.get('epc_warranty_start_date')),
                    parse_datetime(data.get('epc_warranty_expire_date')),
                    data.get('calibration_frequency', ''),
                    data.get('pm_frequency', ''),
                    data.get('visual_inspection_frequency', ''),
                    float(data.get('bess_capacity', 0)) if data.get('bess_capacity') else None,
                    data.get('yom', ''),
                    data.get('nomenclature', ''),
                    data.get('location', ''),
                    json.dumps(data.get('power_model_config')) if data.get('power_model_config') is not None else None,
                    json.dumps(data.get('weather_device_config')) if data.get('weather_device_config') is not None else None,
                    json.dumps(data.get('tilt_configs')) if data.get('tilt_configs') is not None else None
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Device created successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_update_device_list(request):
    """API endpoint to update device list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Updating device {device_id} with data keys: {list(data.keys())}")
            
            if not device_id:
                return JsonResponse({'error': 'Device ID is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Build dynamic update query based on provided fields
                # SECURITY: Whitelist of allowed field names to prevent SQL injection
                ALLOWED_DEVICE_LIST_FIELDS = {
                    'device_name', 'device_code', 'device_type_id', 'device_serial', 'device_model',
                    'device_make', 'latitude', 'longitude', 'optimizer_no', 'parent_code', 'device_type',
                    'software_version', 'country', 'string_no', 'connected_strings', 'device_sub_group',
                    'dc_cap', 'device_source', 'ac_capacity', 'equipment_warranty_start_date',
                    'equipment_warranty_expire_date', 'epc_warranty_start_date', 'epc_warranty_expire_date',
                    'calibration_frequency', 'pm_frequency', 'visual_inspection_frequency', 'bess_capacity',
                    'yom', 'nomenclature', 'location', 'module_datasheet_id', 'modules_in_series',
                    'installation_date', 'tilt_angle', 'azimuth_angle', 'mounting_type', 'expected_soiling_loss',
                    'shading_factor', 'measured_degradation_rate', 'last_performance_test_date', 'operational_notes',
                    'power_model_id', 'model_fallback_enabled', 'weather_device_config', 'tilt_configs'
                    , 'power_model_config'
                }
                
                update_fields = []
                values = []
                
                # Helper function to parse datetime
                def parse_datetime(date_str):
                    if not date_str:
                        return None
                    try:
                        from datetime import datetime
                        # Handle datetime-local format (YYYY-MM-DDTHH:MM)
                        if 'T' in date_str:
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        return None
                
                field_mappings = {
                    'device_name': data.get('device_name'),
                    'device_code': data.get('device_code', ''),
                    'device_type_id': data.get('device_type_id', ''),
                    'device_serial': data.get('device_serial', ''),
                    'device_model': data.get('device_model', ''),
                    'device_make': data.get('device_make', ''),
                    'latitude': float(data.get('latitude', 0)) if data.get('latitude') else 0,
                    'longitude': float(data.get('longitude', 0)) if data.get('longitude') else 0,
                    'optimizer_no': int(data.get('optimizer_no', 0)) if data.get('optimizer_no') else 0,
                    'parent_code': data.get('parent_code', ''),
                    'device_type': data.get('device_type'),
                    'software_version': data.get('software_version', ''),
                    'country': data.get('country'),
                    'string_no': data.get('string_no', ''),
                    'connected_strings': data.get('connected_strings', ''),
                    'device_sub_group': data.get('device_sub_group', ''),
                    'dc_cap': float(data.get('dc_cap', 0)) if data.get('dc_cap') else None,
                    'device_source': data.get('device_source', ''),
                    'ac_capacity': float(data.get('ac_capacity', 0)) if data.get('ac_capacity') else None,
                    'equipment_warranty_start_date': parse_datetime(data.get('equipment_warranty_start_date')),
                    'equipment_warranty_expire_date': parse_datetime(data.get('equipment_warranty_expire_date')),
                    'epc_warranty_start_date': parse_datetime(data.get('epc_warranty_start_date')),
                    'epc_warranty_expire_date': parse_datetime(data.get('epc_warranty_expire_date')),
                    'calibration_frequency': data.get('calibration_frequency', ''),
                    'pm_frequency': data.get('pm_frequency', ''),
                    'visual_inspection_frequency': data.get('visual_inspection_frequency', ''),
                    'bess_capacity': float(data.get('bess_capacity', 0)) if data.get('bess_capacity') else None,
                    'yom': data.get('yom', ''),
                    'nomenclature': data.get('nomenclature', ''),
                    'location': data.get('location', ''),
                    # PV Module Configuration Fields (New - Phase 4)
                    'module_datasheet_id': int(data.get('module_datasheet_id')) if data.get('module_datasheet_id') else None,
                    'modules_in_series': int(data.get('modules_in_series')) if data.get('modules_in_series') else None,
                    'installation_date': data.get('installation_date'),
                    'tilt_angle': float(data.get('tilt_angle')) if data.get('tilt_angle') else None,
                    'azimuth_angle': float(data.get('azimuth_angle')) if data.get('azimuth_angle') else None,
                    'mounting_type': data.get('mounting_type'),
                    'expected_soiling_loss': float(data.get('expected_soiling_loss')) if data.get('expected_soiling_loss') is not None else 2.0,
                    'shading_factor': float(data.get('shading_factor')) if data.get('shading_factor') is not None else 0.0,
                    'measured_degradation_rate': float(data.get('measured_degradation_rate')) if data.get('measured_degradation_rate') else None,
                    'last_performance_test_date': data.get('last_performance_test_date'),
                    'operational_notes': data.get('operational_notes'),
                    'power_model_id': int(data.get('power_model_id')) if data.get('power_model_id') else None,
                    'model_fallback_enabled': bool(data.get('model_fallback_enabled', True)),
                    'power_model_config': data.get('power_model_config'),  # JSON field
                    'weather_device_config': data.get('weather_device_config'),  # JSON field
                    'tilt_configs': data.get('tilt_configs'),  # JSON field
                }
                
                import json as json_module
                for field, value in field_mappings.items():
                    # SECURITY: Only process fields that are in the whitelist and were provided
                    if field in ALLOWED_DEVICE_LIST_FIELDS and field in data:
                        if field in ('power_model_config', 'weather_device_config', 'tilt_configs') and value is not None:
                            # Handle JSONB fields
                            update_fields.append(f"{field} = %s::jsonb")
                            values.append(json_module.dumps(value))
                        else:
                            update_fields.append(f"{field} = %s")
                            values.append(value)
                
                # Execute UPDATE after collecting all fields (still inside cursor context)
                if update_fields:
                    values.append(device_id)  # For WHERE clause
                    update_query = f"""
                        UPDATE device_list 
                        SET {', '.join(update_fields)}
                        WHERE device_id = %s
                    """
                    logger.info(f"Executing update with {len(update_fields)} fields for device {device_id}")
                    logger.debug(f"Update fields: {update_fields}")
                    cursor.execute(update_query, values)
                    rows_affected = cursor.rowcount
                    logger.info(f"Update affected {rows_affected} row(s)")
                    
                    if rows_affected == 0:
                        logger.error(f"No rows updated for device_id: {device_id}")
                        return JsonResponse({
                            'success': False,
                            'error': f'Device {device_id} not found or update failed'
                        }, status=404)
                else:
                    logger.warning(f"No fields to update for device {device_id}")
            
            # Commit the transaction
            logger.info(f"Successfully updated device {device_id}")
            
            return JsonResponse({
                'success': True,
                'message': 'Device updated successfully!',
                'fields_updated': len(update_fields) if 'update_fields' in locals() else 0
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_delete_device_list(request, device_id):
    """API endpoint to delete device list record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for device {device_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM device_list WHERE device_id = %s", [device_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Device {device_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
                
            return JsonResponse({
                'success': True,
                'message': 'Device deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


# Device Mapping CRUD operations
@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_create_device_mapping(request):
    """API endpoint to create new device mapping record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['asset_code', 'device_type', 'oem_tag', 'data_type', 'units', 'metric']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Check if record with same asset_code, metric, device_type already exists
                cursor.execute("""
                    SELECT id FROM device_mapping 
                    WHERE asset_code = %s AND metric = %s AND device_type = %s
                """, [data.get('asset_code'), data.get('metric'), data.get('device_type')])
                
                existing_record = cursor.fetchone()
                if existing_record:
                    return JsonResponse({
                        'error': f'Record already exists with asset_code={data.get("asset_code")}, metric={data.get("metric")}, device_type={data.get("device_type")}'
                    }, status=400)
                
                # Get the next available ID
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM device_mapping")
                next_id = cursor.fetchone()[0]
                
                # Insert into device_mapping table
                cursor.execute("""
                    INSERT INTO device_mapping (
                        id, asset_code, device_type, oem_tag, discription,
                        data_type, units, metric, fault_code, module_no, default_value
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    next_id,
                    ensure_unicode_string(data.get('asset_code')),
                    ensure_unicode_string(data.get('device_type')),
                    ensure_unicode_string(data.get('oem_tag')),
                    ensure_unicode_string(data.get('description', '')),  # Use 'description' from frontend but save as 'discription'
                    ensure_unicode_string(data.get('data_type')),
                    ensure_unicode_string(data.get('units')),
                    ensure_unicode_string(data.get('metric')),
                    ensure_unicode_string(data.get('fault_code', '')),
                    ensure_unicode_string(data.get('module_no', '')),
                    ensure_unicode_string(data.get('default_value', ''))
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Device mapping created successfully!',
                'id': next_id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_update_device_mapping(request):
    """API endpoint to update device mapping record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mapping_id = data.get('id')
            
            if not mapping_id:
                return JsonResponse({'error': 'Mapping ID is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Build dynamic update query based on provided fields
                # SECURITY: Whitelist of allowed field names to prevent SQL injection
                ALLOWED_DEVICE_MAPPING_FIELDS = {
                    'asset_code', 'device_type', 'oem_tag', 'discription', 'data_type',
                    'units', 'metric', 'fault_code', 'module_no', 'default_value'
                }
                
                update_fields = []
                values = []
                
                field_mappings = {
                    'asset_code': ensure_unicode_string(data.get('asset_code')),
                    'device_type': ensure_unicode_string(data.get('device_type')),
                    'oem_tag': ensure_unicode_string(data.get('oem_tag')),
                    'discription': ensure_unicode_string(data.get('description', '')),  # Use 'description' from frontend but save as 'discription'
                    'data_type': ensure_unicode_string(data.get('data_type')),
                    'units': ensure_unicode_string(data.get('units')),
                    'metric': ensure_unicode_string(data.get('metric')),
                    'fault_code': ensure_unicode_string(data.get('fault_code', '')),
                    'module_no': ensure_unicode_string(data.get('module_no', '')),
                    'default_value': ensure_unicode_string(data.get('default_value', ''))
                }
                
                # SECURITY: Only process fields that are in the whitelist
                for field, value in field_mappings.items():
                    # Check if field was provided (handle discription mapping)
                    field_provided = field.replace('discription', 'description') in data
                    if field in ALLOWED_DEVICE_MAPPING_FIELDS and field_provided:
                        # Use identifier quoting to safely handle field names
                        update_fields.append(f'"{field}" = %s')
                        values.append(value)
                
                if update_fields:
                    values.append(mapping_id)  # For WHERE clause
                    # SECURITY: Use parameterized query with validated field names
                    # Field names are now validated against whitelist, values are parameterized
                    query = f"""
                        UPDATE device_mapping 
                        SET {', '.join(update_fields)}
                        WHERE id = %s
                    """
                    cursor.execute(query, values)
            
            return JsonResponse({
                'success': True,
                'message': 'Device mapping updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_delete_device_mapping(request, mapping_id):
    """API endpoint to delete device mapping record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for device mapping {mapping_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM device_mapping WHERE id = %s", [mapping_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Device mapping {mapping_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Device mapping deleted successfully!'
            })
            
        except device_mapping.DoesNotExist:
            return JsonResponse({'error': 'Device mapping not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_device_operating_state(request):
    """API endpoint to create a new device_operating_state row."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.models import DeviceOperatingState

        data = json.loads(request.body)
        adapter_id = ensure_unicode_string(data.get('adapter_id', '')).strip()
        device_type = ensure_unicode_string(data.get('device_type', '')).strip()
        state_value = ensure_unicode_string(data.get('state_value', '')).strip()
        oem_state_label = ensure_unicode_string(data.get('oem_state_label', '')).strip()
        internal_state = ensure_unicode_string(data.get('internal_state', '')).strip()
        is_normal = bool(data.get('is_normal', False))
        fault_code = ensure_unicode_string(data.get('fault_code', '')).strip() or None

        if not adapter_id or not device_type or not state_value or not internal_state:
            return JsonResponse({'error': 'adapter_id, device_type, state_value and internal_state are required'}, status=400)

        obj, created = DeviceOperatingState.objects.update_or_create(
            adapter_id=adapter_id,
            device_type=device_type,
            state_value=state_value,
            defaults={
                'oem_state_label': oem_state_label,
                'internal_state': internal_state,
                'is_normal': is_normal,
                'fault_code': fault_code,
            },
        )
        return JsonResponse(
            {
                'success': True,
                'message': 'Device operating state created successfully!' if created else 'Device operating state updated successfully!',
                'id': obj.id,
            }
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_update_device_operating_state(request):
    """API endpoint to update an existing device_operating_state row."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.models import DeviceOperatingState

        data = json.loads(request.body)
        state_id = data.get('id')
        if not state_id:
            return JsonResponse({'error': 'id is required'}, status=400)

        obj = DeviceOperatingState.objects.get(id=state_id)
        # Updatable fields
        if 'adapter_id' in data:
            obj.adapter_id = ensure_unicode_string(data.get('adapter_id', '')).strip()
        if 'device_type' in data:
            obj.device_type = ensure_unicode_string(data.get('device_type', '')).strip()
        if 'state_value' in data:
            obj.state_value = ensure_unicode_string(data.get('state_value', '')).strip()
        if 'oem_state_label' in data:
            obj.oem_state_label = ensure_unicode_string(data.get('oem_state_label', '')).strip()
        if 'internal_state' in data:
            obj.internal_state = ensure_unicode_string(data.get('internal_state', '')).strip()
        if 'is_normal' in data:
            obj.is_normal = bool(data.get('is_normal'))
        if 'fault_code' in data:
            fc = ensure_unicode_string(data.get('fault_code', '')).strip()
            obj.fault_code = fc or None

        obj.save()
        return JsonResponse({'success': True, 'message': 'Device operating state updated successfully!'})
    except DeviceOperatingState.DoesNotExist:
        return JsonResponse({'error': 'Device operating state not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
def api_delete_device_operating_state(request, state_id):
    """API endpoint to delete device_operating_state row (superuser only)."""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    try:
        from data_collection.models import DeviceOperatingState

        if not request.user.is_superuser:
            return JsonResponse({'error': 'Only superusers can delete records'}, status=403)

        obj = DeviceOperatingState.objects.get(id=state_id)
        obj.delete()
        return JsonResponse({'success': True, 'message': 'Device operating state deleted successfully!'})
    except DeviceOperatingState.DoesNotExist:
        return JsonResponse({'error': 'Device operating state not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Budget Values CRUD operations
@role_required(allowed_roles=['admin'])
@login_required
def api_create_budget_values(request):
    """API endpoint to create a new budget values record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Use raw SQL for unmanaged table
            from django.db import connection
            
            asset_code = ensure_unicode_string(data.get('asset_code', ''))
            month_str = ensure_unicode_string(data.get('month_str', ''))
            
            # Check if record already exists
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM budget_values 
                    WHERE asset_code = %s AND month_str = %s
                """, [asset_code, month_str])
                
                existing_record = cursor.fetchone()
                
                if existing_record:
                    return JsonResponse({'error': f'Budget values already exist for {asset_code} - {month_str}'}, status=400)
                
                # Insert new record
                cursor.execute("""
                    INSERT INTO budget_values (
                        asset_number, asset_code, month_str, month_date,
                        bd_production, bd_ghi, bd_gti
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    ensure_unicode_string(data.get('asset_number', '')),
                    asset_code,
                    month_str,
                    data.get('month_date') if data.get('month_date') else None,
                    float(data.get('bd_production', 0)) if data.get('bd_production') else 0,
                    float(data.get('bd_ghi', 0)) if data.get('bd_ghi') else 0,
                    float(data.get('bd_gti', 0)) if data.get('bd_gti') else 0
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Budget values created successfully!'
            })
            
        except ValueError as e:
            return JsonResponse({'error': f'Invalid data format: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required  
def api_update_budget_values(request):
    """API endpoint to update budget values record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            budget_id = data.get('id')
            
            if not budget_id:
                return JsonResponse({'error': 'Budget ID is required'}, status=400)
            
            # Use raw SQL for unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE budget_values SET
                        asset_number = %s,
                        asset_code = %s,
                        month_str = %s,
                        month_date = %s,
                        bd_production = %s,
                        bd_ghi = %s,
                        bd_gti = %s
                    WHERE id = %s
                """, [
                    ensure_unicode_string(data.get('asset_number', '')),
                    ensure_unicode_string(data.get('asset_code', '')),
                    ensure_unicode_string(data.get('month_str', '')),
                    data.get('month_date') if data.get('month_date') else None,
                    float(data.get('bd_production', 0)) if data.get('bd_production') else 0,
                    float(data.get('bd_ghi', 0)) if data.get('bd_ghi') else 0,
                    float(data.get('bd_gti', 0)) if data.get('bd_gti') else 0,
                    budget_id
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Budget values updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
def api_delete_budget_values(request, budget_id):
    """API endpoint to delete budget values record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for budget values {budget_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM budget_values WHERE id = %s", [budget_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Budget values {budget_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Budget values deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


# IC Budget CRUD operations
@role_required(allowed_roles=['admin'])
@login_required
def api_ic_budget_data(request):
    """API endpoint to fetch paginated IC budget data with filters"""
    if request.method == 'GET':
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 25))
            search = request.GET.get('search', '')
            asset_code_filter = request.GET.get('asset_code', '').strip()
            
            # Use raw SQL to query unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Build filter conditions
                conditions = []
                params = []
                
                # Add asset_code filter
                if asset_code_filter:
                    conditions.append("asset_code = %s")
                    params.append(asset_code_filter)
                
                # Add search filter
                if search:
                    conditions.append("(asset_code ILIKE %s OR asset_number ILIKE %s OR month_str ILIKE %s)")
                    params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
                
                # Build WHERE clause
                search_condition = ""
                if conditions:
                    search_condition = "WHERE " + " AND ".join(conditions)
                
                search_params = params
                
                # Get total count
                count_query = f"SELECT COUNT(*) FROM ic_budget {search_condition}"
                cursor.execute(count_query, search_params)
                total_count = cursor.fetchone()[0]
                
                # Calculate pagination
                offset = (page - 1) * page_size
                total_pages = (total_count + page_size - 1) // page_size
                
                # Get paginated data
                data_query = f"""
                    SELECT id, asset_code, asset_number, month_str, month_date, ic_bd_production
                    FROM ic_budget 
                    {search_condition}
                    ORDER BY asset_code, month_str
                    LIMIT %s OFFSET %s
                """
                cursor.execute(data_query, search_params + [page_size, offset])
                
                columns = [col[0] for col in cursor.description]
                ic_budgets = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Convert dates to strings for JSON serialization
                for ic_budget in ic_budgets:
                    if ic_budget['month_date']:
                        ic_budget['month_date'] = ic_budget['month_date'].strftime('%Y-%m-%d')
            
            return JsonResponse({
                'ic_budgets': ic_budgets,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_count': total_count,
                    'page_size': page_size
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only GET method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_create_ic_budget(request):
    """API endpoint to create new IC budget record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle date formatting
                month_date = data.get('month_date')
                if month_date:
                    try:
                        from datetime import datetime
                        month_date = datetime.strptime(month_date, '%Y-%m-%d').date()
                    except:
                        return JsonResponse({'error': 'Invalid month_date format. Use YYYY-MM-DD'}, status=400)
                
                # Check for existing record based on asset_code and month_date
                cursor.execute("""
                    SELECT id FROM ic_budget 
                    WHERE asset_code = %s AND month_date = %s
                """, [data.get('asset_code'), month_date])
                
                if cursor.fetchone():
                    return JsonResponse({'error': 'IC Budget record already exists for this asset and month date'}, status=400)
                
                # Insert into ic_budget table
                cursor.execute("""
                    INSERT INTO ic_budget (
                        asset_code, asset_number, month_str, month_date, ic_bd_production
                    ) VALUES (%s, %s, %s, %s, %s)
                """, [
                    data.get('asset_code'),
                    data.get('asset_number'),
                    data.get('month_str'),
                    month_date,
                    float(data.get('ic_bd_production'))
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'IC Budget created successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
#@csrf_exempt
def api_update_ic_budget(request):
    """API endpoint to update IC budget record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ic_budget_id = data.get('id')
            
            if not ic_budget_id:
                return JsonResponse({'error': 'IC Budget ID is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle date formatting
                month_date = data.get('month_date')
                if month_date:
                    try:
                        from datetime import datetime
                        month_date = datetime.strptime(month_date, '%Y-%m-%d').date()
                    except:
                        return JsonResponse({'error': 'Invalid month_date format. Use YYYY-MM-DD'}, status=400)
                
                # Update ic_budget table
                cursor.execute("""
                    UPDATE ic_budget 
                    SET asset_code = %s, asset_number = %s, month_str = %s, 
                        month_date = %s, ic_bd_production = %s
                    WHERE id = %s
                """, [
                    data.get('asset_code'),
                    data.get('asset_number'),
                    data.get('month_str'),
                    month_date,
                    float(data.get('ic_bd_production')),
                    ic_budget_id
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'IC Budget updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
def api_delete_ic_budget(request, ic_budget_id):
    """API endpoint to delete IC budget record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for IC budget {ic_budget_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM ic_budget WHERE id = %s", [ic_budget_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"IC Budget {ic_budget_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'IC Budget deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
def api_asset_contracts_data(request):
    """API endpoint to get asset contracts data with pagination."""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()

        contracts = assets_contracts.objects.all().order_by('asset_number')
        if search:
            contracts = contracts.filter(
                models.Q(asset_number__icontains=search)
                | models.Q(asset_code__icontains=search)
                | models.Q(customer_asset_name__icontains=search)
                | models.Q(contractor_name__icontains=search)
                | models.Q(spv_name__icontains=search)
                | models.Q(sp_account_no__icontains=search)
            )

        total_count = contracts.count()
        start = (page - 1) * page_size
        end = start + page_size
        rows = contracts[start:end]

        data = []
        for row in rows:
            d = model_to_dict(row)
            # Normalize dates/decimals for JSON
            for k, v in list(d.items()):
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif v is None:
                    d[k] = None
                else:
                    try:
                        from decimal import Decimal
                        if isinstance(v, Decimal):
                            d[k] = float(v)
                    except Exception:
                        pass
            # Include timestamps too
            d['created_at'] = row.created_at.isoformat() if getattr(row, 'created_at', None) else ''
            d['updated_at'] = row.updated_at.isoformat() if getattr(row, 'updated_at', None) else ''
            data.append(d)

        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size) if page_size else 1,
            'can_delete': bool(getattr(request.user, 'is_superuser', False)),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_asset_contract(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        payload = json.loads(request.body)
        asset_number = (payload.get('asset_number') or '').strip()
        asset_code = (payload.get('asset_code') or '').strip()
        if not asset_number or not asset_code:
            return JsonResponse({'error': 'asset_number and asset_code are required'}, status=400)

        model_fields = {
            f.name: f for f in assets_contracts._meta.fields
            if f.name not in ('id', 'created_at', 'updated_at')
        }
        defaults = {'asset_code': asset_code}
        for k, v in payload.items():
            key = str(k).strip()
            if key in model_fields and key not in ('asset_number',):
                defaults[key] = v
        obj, created = assets_contracts.objects.update_or_create(asset_number=asset_number, defaults=defaults)

        return JsonResponse({
            'success': True,
            'message': 'Asset contract created successfully' if created else 'Asset contract updated successfully',
            'id': obj.id,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_update_asset_contract(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        payload = json.loads(request.body)
        contract_id = payload.get('id')
        if not contract_id:
            return JsonResponse({'error': 'id is required'}, status=400)

        obj = assets_contracts.objects.get(id=contract_id)
        model_fields = {
            f.name: f for f in assets_contracts._meta.fields
            if f.name not in ('id', 'created_at', 'updated_at')
        }
        for k, v in payload.items():
            key = str(k).strip()
            if key in model_fields:
                setattr(obj, key, v)
        obj.save()

        return JsonResponse({'success': True, 'message': 'Asset contract updated successfully'})
    except assets_contracts.DoesNotExist:
        return JsonResponse({'error': 'Asset contract not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
def api_delete_asset_contract(request, contract_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    try:
        obj = assets_contracts.objects.get(id=contract_id)
        obj.delete()
        return JsonResponse({'success': True, 'message': 'Asset contract deleted successfully'})
    except assets_contracts.DoesNotExist:
        return JsonResponse({'error': 'Asset contract not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_calculate_budget_values(request):
    """
    API endpoint to calculate budget values for selected assets and year range (0-n)
    Returns CSV download with calculated budget values
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        import json
        from datetime import datetime, date
        import pytz
        from django.http import HttpResponse
        import csv
        from io import StringIO
        
        data = json.loads(request.body)
        asset_codes = data.get('asset_codes', [])
        from_year = int(data.get('from_year', 0))  # Start year (e.g., 2026)
        to_year = int(data.get('to_year', 0))  # End year (e.g., 2026 or 2030)
        
        if not asset_codes:
            return JsonResponse({'error': 'At least one asset must be selected'}, status=400)
        
        if from_year <= 0 or to_year <= 0:
            return JsonResponse({'error': 'From year and To year must be valid years (e.g., 2026)'}, status=400)
        
        if from_year > to_year:
            return JsonResponse({'error': 'From year must be <= To year'}, status=400)
        
        # Get current year for reference (but calculations will be based on COD year)
        current_date = datetime.now()
        current_year = current_date.year
        
        # Use raw SQL to get asset details and budget values
        from django.db import connection
        
        results = []
        
        with connection.cursor() as cursor:
            # Get asset details
            placeholders = ','.join(['%s'] * len(asset_codes))
            cursor.execute(f"""
                SELECT asset_code, timezone, asset_number, cod, y1_degradation, anual_degradation, capacity
                FROM asset_list
                WHERE asset_code IN ({placeholders})
            """, asset_codes)
            
            assets = cursor.fetchall()
            
            # Get ALL budget values (year 0 values) for each asset - all months
            cursor.execute(f"""
                SELECT asset_code, month_str, bd_production, bd_ghi, bd_gti
                FROM budget_values
                WHERE asset_code IN ({placeholders})
                ORDER BY asset_code, month_str
            """, asset_codes)
            
            # Organize budget values by asset_code and month
            budget_dict = {}
            for row in cursor.fetchall():
                asset_code = row[0]
                month_str = row[1]
                if asset_code not in budget_dict:
                    budget_dict[asset_code] = {}
                budget_dict[asset_code][month_str] = {
                    'bd_production': float(row[2]) if row[2] else 0,
                    'bd_ghi': float(row[3]) if row[3] else 0,
                    'bd_gti': float(row[4]) if row[4] else 0,
                }
            
            # Month string to number mapping
            month_order = {
                'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
            }
            
            # Process each asset
            for asset_code, asset_timezone, asset_number, cod, y1_degradation, anual_degradation, capacity in assets:
                if asset_code not in budget_dict or not budget_dict[asset_code]:
                    # Skip assets without budget values
                    continue
                
                # Get COD month and year - this is the base (Year 1 starts from COD month)
                if not cod:
                    # Skip assets without COD
                    continue
                
                cod_year = cod.year
                cod_month = cod.month  # COD month (1-12)
                
                # Convert degradation percentages to decimals
                y1_degradation_decimal = float(y1_degradation) / 100 if y1_degradation else 0
                anual_degradation_decimal = float(anual_degradation) / 100 if anual_degradation else 0
                
                # Get all months for this asset
                asset_budget_months = budget_dict[asset_code]
                
                # Calculate for each month and each year from from_year to to_year
                for month_str, bd_values in asset_budget_months.items():
                    bd_production = bd_values['bd_production']
                    bd_ghi = bd_values['bd_ghi']
                    bd_gti = bd_values['bd_gti']
                    
                    # Convert month_str to month number (1-12)
                    target_month = month_order.get(month_str.upper(), None)
                    if target_month is None:
                        # Skip invalid month strings
                        continue
                    
                    # Calculate for each year from from_year to to_year
                    for target_year in range(from_year, to_year + 1):
                        # Calculate months elapsed since COD
                        # Formula: (target_year - cod_year) * 12 + (target_month - cod_month)
                        months_from_cod = (target_year - cod_year) * 12 + (target_month - cod_month)
                        
                        # Skip if target month is before COD month (negative months_from_cod)
                        if months_from_cod < 0:
                            continue
                        
                        # Calculate years_from_cod based on months elapsed
                        # Year 1: months 0-11 (from COD month to 11 months after)
                        # Year 2: months 12-23
                        # Year 3: months 24-35
                        # Formula: floor(months_from_cod / 12) + 1
                        years_from_cod = (months_from_cod // 12) + 1
                        
                        # Year offset for display (Year 1 = offset 1, Year 2 = offset 2, etc.)
                        year_offset = years_from_cod
                        
                        # Calculate monthly expected MWh using the alternative formula
                        # Formula: 
                        # - Year 1: base * (1 - y1_degradation) [months 0-11 from COD]
                        # - Year 2+: base * (1 - y1_degradation) * (1 - annual_degradation)^(year-1)
                        # 
                        # NOTE: This is a MONTHLY value, not daily. Daily values may be added in the future.
                        # 
                        # This is the typical degradation formula used in solar PV systems:
                        # Year 1 has initial degradation (y1_degradation) applied from COD month
                        # Subsequent years have annual degradation applied cumulatively
                        # 
                        # Year calculation is based on months elapsed since COD:
                        # - Year 1: COD month to 11 months after (months 0-11)
                        # - Year 2: 12-23 months after COD
                        # - Year 3: 24-35 months after COD, etc.
                        try:
                            if years_from_cod == 1:
                                # Year 1: Apply initial degradation only
                                monthly_expected_mwh = bd_production * (1 - y1_degradation_decimal)
                            else:
                                # Year 2+: Apply initial degradation + cumulative annual degradation
                                # Formula: base * (1 - y1_degradation) * (1 - annual_degradation)^(years_from_cod - 1)
                                annual_degradation_factor = (1 - anual_degradation_decimal) ** (years_from_cod - 1)
                                monthly_expected_mwh = bd_production * (1 - y1_degradation_decimal) * annual_degradation_factor
                        except ZeroDivisionError:
                            print(f"Error calculating for {asset_code} month {month_str} year {target_year}: Division by zero")
                            monthly_expected_mwh = 0
                        except ValueError as ve:
                            print(f"Error calculating for {asset_code} month {month_str} year {target_year}: Invalid value - {str(ve)}")
                            monthly_expected_mwh = 0
                        except OverflowError:
                            print(f"Error calculating for {asset_code} month {month_str} year {target_year}: Calculation overflow (years_from_cod={years_from_cod} too large)")
                            monthly_expected_mwh = 0
                        except Exception as e:
                            print(f"Error calculating for {asset_code} month {month_str} year {target_year}: {str(e)}")
                            monthly_expected_mwh = 0
                        
                        # Budget irradiation remains the same (bd_gti) - this is also monthly
                        monthly_budget_irradiation_mwh = bd_gti
                        
                        results.append({
                            'asset_code': asset_code,
                            'asset_number': asset_number or '',
                            'year': year_offset,
                            'target_year': target_year,
                            'month_str': month_str,
                            'bd_production': bd_production,
                            'monthly_expected_mwh': round(monthly_expected_mwh, 4),
                            'monthly_budget_irradiation_mwh': round(monthly_budget_irradiation_mwh, 4),
                            'bd_ghi': bd_ghi,
                            'bd_gti': bd_gti,
                            'y1_degradation': y1_degradation,
                            'anual_degradation': anual_degradation,
                            'cod_year': cod_year,
                            'cod_month': cod_month,
                            'months_from_cod': months_from_cod,
                            'years_from_cod': years_from_cod,
                        })
        
        # Sort results: first by asset_code, then by target_year, then by month (JAN, FEB, MAR, ..., DEC)
        
        def sort_key(result):
            # Sort by: asset_code, target_year, month_order
            month = result.get('month_str', '')
            month_num = month_order.get(month.upper(), 99)  # Unknown months go to end
            return (
                result.get('asset_code', ''),
                result.get('target_year', 0),
                month_num
            )
        
        results.sort(key=sort_key)
        
        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Asset Code', 'Asset Number', 'Year', 'Target Year', 'Month',
            'BD Production (Year 0)', 'Monthly Expected MWh', 'Monthly Budget Irradiation MWh',
            'BD GHI', 'BD GTI', 'Y1 Degradation %', 'Annual Degradation %',
            'COD Year', 'COD Month', 'Months from COD', 'Years from COD'
        ])
        
        # Write data
        for result in results:
            writer.writerow([
                result['asset_code'],
                result['asset_number'],
                result['year'],
                result['target_year'],
                result['month_str'],
                result['bd_production'],
                result['monthly_expected_mwh'],
                result['monthly_budget_irradiation_mwh'],
                result['bd_ghi'],
                result['bd_gti'],
                result['y1_degradation'],
                result['anual_degradation'],
                result['cod_year'],
                result['cod_month'],
                result['months_from_cod'],
                result['years_from_cod'],
            ])
        
        # Create HTTP response with UTF-8 BOM for Excel compatibility
        csv_content = '\ufeff' + output.getvalue()
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="calculated_budget_values_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error calculating budget values: {str(e)}'}, status=500)
