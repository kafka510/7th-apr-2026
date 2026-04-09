"""
Spare Management API Views
CRUD operations for spare management tables with admin/superuser permissions
"""
import math
import json
from django.db import models, transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q

from accounts.decorators import role_required
from ..models import (
    SpareMaster,
    LocationMaster,
    SpareSiteMap,
    StockBalance,
    StockEntry,
    StockIssue,
    StockLedger,
    InventoryAuditLog,
    AssetList,
)
from .shared.decorators import superuser_required


def log_inventory_audit(
    user, action, entity_type, entity_id, entity_name, changes=None, ip_address=None
):
    """Helper to log inventory audit actions"""
    try:
        InventoryAuditLog.objects.create(
            user=user,
            user_name=user.get_full_name() or user.username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            ip_address=ip_address,
            changes=changes or {},
        )
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log inventory audit: {str(e)}")


# ============================================================================
# SPARE MASTER APIs
# ============================================================================

@role_required(allowed_roles=['admin'])
@login_required
def api_spare_master_list(request):
    """API endpoint to get spare master list with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()
        
        spares = SpareMaster.objects.all()
        
        # Apply search filter
        if search:
            spares = spares.filter(
                Q(spare_code__icontains=search) |
                Q(spare_name__icontains=search) |
                Q(category__icontains=search) |
                Q(description__icontains=search)
            )
        
        total_count = spares.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        spares_page = spares[start:end]
        
        data = []
        for spare in spares_page:
            data.append({
                'spare_id': spare.spare_id,
                'spare_code': spare.spare_code,
                'spare_name': spare.spare_name,
                'description': spare.description or '',
                'category': spare.category or '',
                'unit': spare.unit,
                'min_stock': spare.min_stock,
                'max_stock': spare.max_stock,
                'is_critical': spare.is_critical,
            })
        
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
        logger.error(f"Error in api_spare_master_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_spare_master(request):
    """API endpoint to create new spare master record"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('spare_code') or not data.get('spare_name') or not data.get('unit'):
            return JsonResponse({
                'error': 'Missing required fields: spare_code, spare_name, unit'
            }, status=400)
        
        # Check for duplicate spare_code
        if SpareMaster.objects.filter(spare_code=data['spare_code']).exists():
            return JsonResponse({
                'error': f"Spare code '{data['spare_code']}' already exists"
            }, status=400)
        
        with transaction.atomic():
            spare = SpareMaster.objects.create(
                spare_code=data['spare_code'],
                spare_name=data['spare_name'],
                description=data.get('description', ''),
                category=data.get('category', ''),
                unit=data['unit'],
                min_stock=data.get('min_stock'),
                max_stock=data.get('max_stock'),
                is_critical=data.get('is_critical', False),
            )
            
            # Log audit
            log_inventory_audit(
                user=request.user,
                action='CREATE',
                entity_type='SpareMaster',
                entity_id=spare.spare_id,
                entity_name=f"{spare.spare_code} - {spare.spare_name}",
                changes={'created': data},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Spare {spare.spare_code} created successfully',
            'spare_id': spare.spare_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_create_spare_master: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_update_spare_master(request, spare_id):
    """API endpoint to update spare master record"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        spare = SpareMaster.objects.get(spare_id=spare_id)
        data = json.loads(request.body)
        
        # Store old values for audit
        old_values = {
            'spare_name': spare.spare_name,
            'description': spare.description,
            'category': spare.category,
            'unit': spare.unit,
            'min_stock': spare.min_stock,
            'max_stock': spare.max_stock,
            'is_critical': spare.is_critical,
        }
        
        # Update fields (spare_code cannot be changed)
        if 'spare_name' in data:
            spare.spare_name = data['spare_name']
        if 'description' in data:
            spare.description = data.get('description', '')
        if 'category' in data:
            spare.category = data.get('category', '')
        if 'unit' in data:
            spare.unit = data['unit']
        if 'min_stock' in data:
            spare.min_stock = data.get('min_stock')
        if 'max_stock' in data:
            spare.max_stock = data.get('max_stock')
        if 'is_critical' in data:
            spare.is_critical = data.get('is_critical', False)
        
        with transaction.atomic():
            spare.save()
            
            # Log audit
            changes = {k: {'old': old_values.get(k), 'new': getattr(spare, k)} for k in old_values if old_values.get(k) != getattr(spare, k)}
            log_inventory_audit(
                user=request.user,
                action='UPDATE',
                entity_type='SpareMaster',
                entity_id=spare.spare_id,
                entity_name=f"{spare.spare_code} - {spare.spare_name}",
                changes=changes,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Spare {spare.spare_code} updated successfully'
        })
        
    except SpareMaster.DoesNotExist:
        return JsonResponse({'error': 'Spare not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_update_spare_master: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@login_required
def api_delete_spare_master(request, spare_id):
    """API endpoint to delete spare master record (superuser only)"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    
    try:
        spare = SpareMaster.objects.get(spare_id=spare_id)
        spare_code = spare.spare_code
        
        # Check if spare is used in any stock transactions
        if StockEntry.objects.filter(spare=spare).exists() or StockIssue.objects.filter(spare=spare).exists():
            return JsonResponse({
                'error': f'Cannot delete spare {spare_code}: it has stock transactions'
            }, status=400)
        
        with transaction.atomic():
            # Log audit before deletion
            log_inventory_audit(
                user=request.user,
                action='DELETE',
                entity_type='SpareMaster',
                entity_id=spare.spare_id,
                entity_name=f"{spare.spare_code} - {spare.spare_name}",
                changes={'deleted': True},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            spare.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Spare {spare_code} deleted successfully'
        })
        
    except SpareMaster.DoesNotExist:
        return JsonResponse({'error': 'Spare not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_delete_spare_master: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# LOCATION MASTER APIs
# ============================================================================

@role_required(allowed_roles=['admin'])
@login_required
def api_location_master_list(request):
    """API endpoint to get location master list with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()
        
        locations = LocationMaster.objects.all()
        
        # Apply search filter
        if search:
            locations = locations.filter(
                Q(location_code__icontains=search) |
                Q(location_name__icontains=search) |
                Q(location_type__icontains=search)
            )
        
        total_count = locations.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        locations_page = locations[start:end]
        
        data = []
        for location in locations_page:
            data.append({
                'location_id': location.location_id,
                'location_code': location.location_code,
                'location_name': location.location_name,
                'location_type': location.location_type or '',
            })
        
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
        logger.error(f"Error in api_location_master_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_location_master(request):
    """API endpoint to create new location master record"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('location_code') or not data.get('location_name'):
            return JsonResponse({
                'error': 'Missing required fields: location_code, location_name'
            }, status=400)
        
        # Check for duplicate location_code
        if LocationMaster.objects.filter(location_code=data['location_code']).exists():
            return JsonResponse({
                'error': f"Location code '{data['location_code']}' already exists"
            }, status=400)
        
        with transaction.atomic():
            location = LocationMaster.objects.create(
                location_code=data['location_code'],
                location_name=data['location_name'],
                location_type=data.get('location_type', ''),
            )
            
            # Log audit
            log_inventory_audit(
                user=request.user,
                action='CREATE',
                entity_type='LocationMaster',
                entity_id=location.location_id,
                entity_name=f"{location.location_code} - {location.location_name}",
                changes={'created': data},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Location {location.location_code} created successfully',
            'location_id': location.location_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_create_location_master: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_update_location_master(request, location_id):
    """API endpoint to update location master record"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        location = LocationMaster.objects.get(location_id=location_id)
        data = json.loads(request.body)
        
        # Store old values for audit
        old_values = {
            'location_name': location.location_name,
            'location_type': location.location_type,
        }
        
        # Update fields (location_code cannot be changed)
        if 'location_name' in data:
            location.location_name = data['location_name']
        if 'location_type' in data:
            location.location_type = data.get('location_type', '')
        
        with transaction.atomic():
            location.save()
            
            # Log audit
            changes = {k: {'old': old_values.get(k), 'new': getattr(location, k)} for k in old_values if old_values.get(k) != getattr(location, k)}
            log_inventory_audit(
                user=request.user,
                action='UPDATE',
                entity_type='LocationMaster',
                entity_id=location.location_id,
                entity_name=f"{location.location_code} - {location.location_name}",
                changes=changes,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Location {location.location_code} updated successfully'
        })
        
    except LocationMaster.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_update_location_master: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@login_required
def api_delete_location_master(request, location_id):
    """API endpoint to delete location master record (superuser only)"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    
    try:
        location = LocationMaster.objects.get(location_id=location_id)
        location_code = location.location_code
        
        # Check if location is used in any stock transactions
        if StockEntry.objects.filter(location=location).exists() or StockIssue.objects.filter(location=location).exists():
            return JsonResponse({
                'error': f'Cannot delete location {location_code}: it has stock transactions'
            }, status=400)
        
        with transaction.atomic():
            # Log audit before deletion
            log_inventory_audit(
                user=request.user,
                action='DELETE',
                entity_type='LocationMaster',
                entity_id=location.location_id,
                entity_name=f"{location.location_code} - {location.location_name}",
                changes={'deleted': True},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            location.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Location {location_code} deleted successfully'
        })
        
    except LocationMaster.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_delete_location_master: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# SPARE SITE MAP APIs
# ============================================================================

@role_required(allowed_roles=['admin'])
@login_required
def api_spare_site_map_list(request):
    """API endpoint to get spare-site-location mapping list with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()
        asset_code_filter = request.GET.get('asset_code', '').strip()
        spare_code_filter = request.GET.get('spare_code', '').strip()
        location_code_filter = request.GET.get('location_code', '').strip()
        
        mappings = SpareSiteMap.objects.select_related('spare', 'asset', 'location').all()
        
        # Apply filters
        if asset_code_filter:
            mappings = mappings.filter(asset__asset_code=asset_code_filter)
        if spare_code_filter:
            mappings = mappings.filter(spare__spare_code=spare_code_filter)
        if location_code_filter:
            mappings = mappings.filter(location__location_code=location_code_filter)
        
        # Apply search filter
        if search:
            mappings = mappings.filter(
                Q(asset__asset_code__icontains=search) |
                Q(asset__asset_name__icontains=search) |
                Q(spare__spare_code__icontains=search) |
                Q(spare__spare_name__icontains=search) |
                Q(location__location_code__icontains=search) |
                Q(location__location_name__icontains=search)
            )
        
        total_count = mappings.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        mappings_page = mappings[start:end]
        
        data = []
        for mapping in mappings_page:
            data.append({
                'map_id': mapping.map_id,
                'spare_id': mapping.spare.spare_id,
                'spare_code': mapping.spare.spare_code,
                'spare_name': mapping.spare.spare_name,
                'asset_code': mapping.asset.asset_code,
                'asset_name': mapping.asset.asset_name,
                'location_id': mapping.location.location_id,
                'location_code': mapping.location.location_code,
                'location_name': mapping.location.location_name,
                'is_active': mapping.is_active,
                'created_at': mapping.created_at.isoformat() if mapping.created_at else '',
            })
        
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
        logger.error(f"Error in api_spare_site_map_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_spare_site_map(request):
    """API endpoint to create new spare-site-location mapping"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('spare_id') or not data.get('asset_code') or not data.get('location_id'):
            return JsonResponse({
                'error': 'Missing required fields: spare_id, asset_code, location_id'
            }, status=400)
        
        # Validate foreign keys exist
        try:
            spare = SpareMaster.objects.get(spare_id=data['spare_id'])
            asset = AssetList.objects.get(asset_code=data['asset_code'])
            location = LocationMaster.objects.get(location_id=data['location_id'])
        except (SpareMaster.DoesNotExist, AssetList.DoesNotExist, LocationMaster.DoesNotExist) as e:
            return JsonResponse({
                'error': f'Invalid reference: {str(e)}'
            }, status=400)
        
        # Check for duplicate mapping
        if SpareSiteMap.objects.filter(
            spare=spare, asset=asset, location=location
        ).exists():
            return JsonResponse({
                'error': f'Mapping already exists for {spare.spare_code} / {asset.asset_code} / {location.location_code}'
            }, status=400)
        
        with transaction.atomic():
            mapping = SpareSiteMap.objects.create(
                spare=spare,
                asset=asset,
                location=location,
                is_active=data.get('is_active', True),
            )
            
            # Log audit
            log_inventory_audit(
                user=request.user,
                action='CREATE',
                entity_type='SpareSiteMap',
                entity_id=mapping.map_id,
                entity_name=f"{asset.asset_code} / {location.location_code} / {spare.spare_code}",
                changes={'created': data},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Spare-site-location mapping created successfully',
            'map_id': mapping.map_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_create_spare_site_map: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_update_spare_site_map(request, map_id):
    """API endpoint to update spare-site-location mapping"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        mapping = SpareSiteMap.objects.get(map_id=map_id)
        data = json.loads(request.body)
        
        # Store old values for audit
        old_values = {
            'is_active': mapping.is_active,
        }
        
        # Update fields (FKs cannot be changed - delete and recreate if needed)
        if 'is_active' in data:
            mapping.is_active = data.get('is_active', True)
        
        with transaction.atomic():
            mapping.save()
            
            # Log audit
            changes = {k: {'old': old_values.get(k), 'new': getattr(mapping, k)} for k in old_values if old_values.get(k) != getattr(mapping, k)}
            log_inventory_audit(
                user=request.user,
                action='UPDATE',
                entity_type='SpareSiteMap',
                entity_id=mapping.map_id,
                entity_name=f"{mapping.asset.asset_code} / {mapping.location.location_code} / {mapping.spare.spare_code}",
                changes=changes,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Spare-site-location mapping updated successfully'
        })
        
    except SpareSiteMap.DoesNotExist:
        return JsonResponse({'error': 'Mapping not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_update_spare_site_map: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@login_required
def api_delete_spare_site_map(request, map_id):
    """API endpoint to delete spare-site-location mapping (superuser only)"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    
    try:
        mapping = SpareSiteMap.objects.select_related('spare', 'asset', 'location').get(map_id=map_id)
        entity_name = f"{mapping.asset.asset_code} / {mapping.location.location_code} / {mapping.spare.spare_code}"
        
        with transaction.atomic():
            # Log audit before deletion
            log_inventory_audit(
                user=request.user,
                action='DELETE',
                entity_type='SpareSiteMap',
                entity_id=mapping.map_id,
                entity_name=entity_name,
                changes={'deleted': True},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            mapping.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Spare-site-location mapping deleted successfully'
        })
        
    except SpareSiteMap.DoesNotExist:
        return JsonResponse({'error': 'Mapping not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_delete_spare_site_map: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# STOCK BALANCE APIs (Read-only view)
# ============================================================================

@role_required(allowed_roles=['admin'])
@login_required
def api_stock_balance_list(request):
    """API endpoint to get stock balance list with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()
        asset_code_filter = request.GET.get('asset_code', '').strip()
        spare_code_filter = request.GET.get('spare_code', '').strip()
        location_code_filter = request.GET.get('location_code', '').strip()
        
        balances = StockBalance.objects.select_related('spare', 'location').all()
        
        # Apply filters
        if asset_code_filter:
            # Filter by asset via SpareSiteMap
            balances = balances.filter(
                spare__site_mappings__asset__asset_code=asset_code_filter,
                spare__site_mappings__is_active=True
            ).distinct()
        if spare_code_filter:
            balances = balances.filter(spare__spare_code=spare_code_filter)
        if location_code_filter:
            balances = balances.filter(location__location_code=location_code_filter)
        
        # Apply search filter
        if search:
            balances = balances.filter(
                Q(spare__spare_code__icontains=search) |
                Q(spare__spare_name__icontains=search) |
                Q(location__location_code__icontains=search) |
                Q(location__location_name__icontains=search)
            )
        
        total_count = balances.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        balances_page = balances[start:end]
        
        data = []
        for balance in balances_page:
            data.append({
                'stock_balance_id': balance.stock_balance_id,
                'spare_id': balance.spare.spare_id,
                'spare_code': balance.spare_code,
                'spare_name': balance.spare.spare_name,
                'location_id': balance.location.location_id,
                'location_code': balance.location_code,
                'location_name': balance.location.location_name,
                'quantity': float(balance.quantity),
                'unit': balance.unit,
                'last_updated': balance.last_updated.isoformat() if balance.last_updated else '',
            })
        
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
        logger.error(f"Error in api_stock_balance_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# STOCK ENTRY APIs (Stock IN transactions)
# ============================================================================

@role_required(allowed_roles=['admin'])
@login_required
def api_stock_entry_list(request):
    """API endpoint to get stock entry list with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()
        asset_code_filter = request.GET.get('asset_code', '').strip()
        spare_code_filter = request.GET.get('spare_code', '').strip()
        location_code_filter = request.GET.get('location_code', '').strip()
        
        entries = StockEntry.objects.select_related('spare', 'location', 'performed_by').all()
        
        # Apply filters
        if asset_code_filter:
            # Filter by asset via SpareSiteMap
            entries = entries.filter(
                spare__site_mappings__asset__asset_code=asset_code_filter,
                spare__site_mappings__is_active=True
            ).distinct()
        if spare_code_filter:
            entries = entries.filter(spare__spare_code=spare_code_filter)
        if location_code_filter:
            entries = entries.filter(location__location_code=location_code_filter)
        
        # Apply search filter
        if search:
            entries = entries.filter(
                Q(spare__spare_code__icontains=search) |
                Q(spare__spare_name__icontains=search) |
                Q(location__location_code__icontains=search) |
                Q(reference_number__icontains=search)
            )
        
        total_count = entries.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        entries_page = entries[start:end]
        
        data = []
        for entry in entries_page:
            data.append({
                'entry_id': entry.entry_id,
                'spare_id': entry.spare.spare_id,
                'spare_code': entry.spare_code,
                'spare_name': entry.spare.spare_name,
                'location_id': entry.location.location_id,
                'location_code': entry.location_code,
                'location_name': entry.location.location_name,
                'quantity': float(entry.quantity),
                'unit': entry.spare.unit,
                'entry_type': entry.entry_type,
                'reference_number': entry.reference_number or '',
                'remarks': entry.remarks or '',
                'entry_date': entry.entry_date.isoformat() if entry.entry_date else '',
                'performed_by': entry.performed_by.username,
            })
        
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
        logger.error(f"Error in api_stock_entry_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_stock_entry(request):
    """API endpoint to create stock entry (IN transaction) and update balance + ledger"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('spare_id') or not data.get('location_id') or not data.get('quantity') or not data.get('entry_type'):
            return JsonResponse({
                'error': 'Missing required fields: spare_id, location_id, quantity, entry_type'
            }, status=400)
        
        # Validate foreign keys
        try:
            spare = SpareMaster.objects.get(spare_id=data['spare_id'])
            location = LocationMaster.objects.get(location_id=data['location_id'])
        except (SpareMaster.DoesNotExist, LocationMaster.DoesNotExist) as e:
            return JsonResponse({
                'error': f'Invalid reference: {str(e)}'
            }, status=400)
        
        quantity = float(data['quantity'])
        if quantity <= 0:
            return JsonResponse({
                'error': 'Quantity must be greater than 0'
            }, status=400)
        
        with transaction.atomic():
            # Create stock entry
            entry = StockEntry.objects.create(
                spare=spare,
                spare_code=spare.spare_code,
                location=location,
                location_code=location.location_code,
                quantity=quantity,
                entry_type=data['entry_type'],
                reference_number=data.get('reference_number', ''),
                remarks=data.get('remarks', ''),
                entry_date=timezone.now(),
                performed_by=request.user,
            )
            
            # Update or create stock balance
            balance, created = StockBalance.objects.get_or_create(
                spare=spare,
                location=location,
                defaults={
                    'spare_code': spare.spare_code,
                    'location_code': location.location_code,
                    'quantity': quantity,
                    'unit': spare.unit,
                }
            )
            if not created:
                balance.quantity += quantity
                balance.save()
            
            # Create ledger entry
            ledger_entry = StockLedger.objects.create(
                spare=spare,
                spare_code=spare.spare_code,
                location_code=location.location_code,
                transaction_type='IN',
                quantity=quantity,
                balance_after=balance.quantity,
                reference=data.get('reference_number', ''),
                remarks=data.get('remarks', ''),
                performed_by=request.user,
            )
            
            # Log audit
            log_inventory_audit(
                user=request.user,
                action='CREATE',
                entity_type='StockEntry',
                entity_id=entry.entry_id,
                entity_name=f"IN {spare.spare_code} {quantity} @ {location.location_code}",
                changes={'created': data, 'balance_after': float(balance.quantity)},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Stock entry created successfully. New balance: {balance.quantity} {spare.unit}',
            'entry_id': entry.entry_id,
            'balance_after': float(balance.quantity)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid value: {str(e)}'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_create_stock_entry: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# STOCK ISSUE APIs (Stock OUT transactions)
# ============================================================================

@role_required(allowed_roles=['admin'])
@login_required
def api_stock_issue_list(request):
    """API endpoint to get stock issue list with pagination and filters"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '').strip()
        asset_code_filter = request.GET.get('asset_code', '').strip()
        spare_code_filter = request.GET.get('spare_code', '').strip()
        location_code_filter = request.GET.get('location_code', '').strip()
        ticket_id_filter = request.GET.get('ticket_id', '').strip()
        
        issues = StockIssue.objects.select_related('spare', 'location', 'performed_by', 'ticket').all()
        
        # Apply filters
        if asset_code_filter:
            # Filter by asset via SpareSiteMap
            issues = issues.filter(
                spare__site_mappings__asset__asset_code=asset_code_filter,
                spare__site_mappings__is_active=True
            ).distinct()
        if spare_code_filter:
            issues = issues.filter(spare__spare_code=spare_code_filter)
        if location_code_filter:
            issues = issues.filter(location__location_code=location_code_filter)
        if ticket_id_filter:
            issues = issues.filter(ticket_id=ticket_id_filter)
        
        # Apply search filter
        if search:
            issues = issues.filter(
                Q(spare__spare_code__icontains=search) |
                Q(spare__spare_name__icontains=search) |
                Q(location__location_code__icontains=search) |
                Q(issued_to__icontains=search)
            )
        
        total_count = issues.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        issues_page = issues[start:end]
        
        data = []
        for issue in issues_page:
            data.append({
                'issue_id': issue.issue_id,
                'spare_id': issue.spare.spare_id,
                'spare_code': issue.spare_code,
                'spare_name': issue.spare.spare_name,
                'location_id': issue.location.location_id,
                'location_code': issue.location_code,
                'location_name': issue.location.location_name,
                'quantity': float(issue.quantity),
                'unit': issue.spare.unit,
                'issue_type': issue.issue_type,
                'ticket_id': str(issue.ticket.id) if issue.ticket else '',
                'ticket_number': issue.ticket.ticket_number if issue.ticket else '',
                'issued_to': issue.issued_to or '',
                'remarks': issue.remarks or '',
                'issue_date': issue.issue_date.isoformat() if issue.issue_date else '',
                'performed_by': issue.performed_by.username,
            })
        
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
        logger.error(f"Error in api_stock_issue_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_create_stock_issue(request):
    """API endpoint to create stock issue (OUT transaction) and update balance + ledger"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('spare_id') or not data.get('location_id') or not data.get('quantity') or not data.get('issue_type'):
            return JsonResponse({
                'error': 'Missing required fields: spare_id, location_id, quantity, issue_type'
            }, status=400)
        
        # Validate foreign keys
        try:
            spare = SpareMaster.objects.get(spare_id=data['spare_id'])
            location = LocationMaster.objects.get(location_id=data['location_id'])
        except (SpareMaster.DoesNotExist, LocationMaster.DoesNotExist) as e:
            return JsonResponse({
                'error': f'Invalid reference: {str(e)}'
            }, status=400)
        
        quantity = float(data['quantity'])
        if quantity <= 0:
            return JsonResponse({
                'error': 'Quantity must be greater than 0'
            }, status=400)
        
        # Validate ticket_id if provided
        ticket = None
        if data.get('ticket_id'):
            try:
                from ticketing.models import Ticket
                ticket = Ticket.objects.get(id=data['ticket_id'])
            except Exception:
                return JsonResponse({
                    'error': f'Invalid ticket_id: {data["ticket_id"]}'
                }, status=400)
        
        with transaction.atomic():
            # Check available stock
            try:
                balance = StockBalance.objects.get(spare=spare, location=location)
                if balance.quantity < quantity:
                    return JsonResponse({
                        'error': f'Insufficient stock. Available: {balance.quantity} {spare.unit}, Requested: {quantity} {spare.unit}'
                    }, status=400)
            except StockBalance.DoesNotExist:
                return JsonResponse({
                    'error': f'No stock available for {spare.spare_code} at {location.location_code}'
                }, status=400)
            
            # Create stock issue
            issue = StockIssue.objects.create(
                spare=spare,
                spare_code=spare.spare_code,
                location=location,
                location_code=location.location_code,
                quantity=quantity,
                issue_type=data['issue_type'],
                ticket=ticket,
                issued_to=data.get('issued_to', ''),
                remarks=data.get('remarks', ''),
                issue_date=timezone.now(),
                performed_by=request.user,
            )
            
            # Update stock balance
            balance.quantity -= quantity
            balance.save()
            
            # Create ledger entry
            ledger_entry = StockLedger.objects.create(
                spare=spare,
                spare_code=spare.spare_code,
                location_code=location.location_code,
                transaction_type='OUT',
                quantity=quantity,
                balance_after=balance.quantity,
                reference=str(issue.issue_id) if issue.issue_id else '',
                remarks=data.get('remarks', ''),
                performed_by=request.user,
            )
            
            # Log audit
            log_inventory_audit(
                user=request.user,
                action='CREATE',
                entity_type='StockIssue',
                entity_id=issue.issue_id,
                entity_name=f"OUT {spare.spare_code} {quantity} @ {location.location_code}",
                changes={'created': data, 'balance_after': float(balance.quantity)},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Stock issue created successfully. Remaining balance: {balance.quantity} {spare.unit}',
            'issue_id': issue.issue_id,
            'balance_after': float(balance.quantity)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid value: {str(e)}'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_create_stock_issue: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
