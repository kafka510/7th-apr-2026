"""Data-collection adapter registry and AssetAdapterConfig / AdapterAccount CRUD.

Used for SolarGIS and other data-acquisition adapters. Add/edit: admin;
delete sensitive rows: superuser only. Adapter IDs come from
``data_collection.adapters``; create/update accepts registered ``adapter_id`` values.
"""
import json
import math

from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse

from accounts.decorators import role_required_api
from ..shared.decorators import superuser_required
from ..shared.utilities import ensure_unicode_string

from .masking import _mask_adapter_config


@role_required_api(allowed_roles=['admin'])
@login_required
def api_data_collection_adapter_ids(request):
    """Return list of data-collection adapter IDs for the UI dropdown."""
    try:
        from data_collection.adapters import get_registered_ids
        from data_collection.models import AdapterAccount, AssetAdapterConfig

        registered = set(get_registered_ids() or [])
        # Also include any adapter IDs already present in DB (for legacy/configured rows).
        in_db = set(AdapterAccount.objects.values_list("adapter_id", flat=True).distinct())
        in_db |= set(AssetAdapterConfig.objects.values_list("adapter_id", flat=True).distinct())

        adapter_ids = sorted({*registered, *in_db})
        return JsonResponse({"adapter_ids": adapter_ids})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_asset_adapter_config_data(request):
    """API endpoint to get AssetAdapterConfig data with pagination and filters."""
    try:
        from data_collection.models import AssetAdapterConfig

        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        adapter_id_filter = request.GET.get('adapter_id', '').strip()
        asset_code_filter = request.GET.get('asset_code', '').strip()

        configs = AssetAdapterConfig.objects.all().select_related('adapter_account').order_by('asset_code')
        if adapter_id_filter:
            configs = configs.filter(adapter_id=adapter_id_filter)
        if asset_code_filter:
            configs = configs.filter(asset_code__icontains=asset_code_filter)
        if search:
            configs = configs.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(adapter_id__icontains=search)
            )

        total_count = configs.count()
        start = (page - 1) * page_size
        end = start + page_size
        configs_page = list(configs[start:end])

        data = []
        for obj in configs_page:
            acc = getattr(obj, 'adapter_account', None)
            raw_config_masked = _mask_adapter_config(obj.config or {}, obj.adapter_id)
            # Merged account + per-asset overrides (what acquisition actually uses); masked for API safety.
            try:
                effective_masked = _mask_adapter_config(
                    obj.get_effective_config() or {},
                    obj.adapter_id,
                )
            except Exception:
                effective_masked = raw_config_masked
            row = {
                'id': obj.id,
                'asset_code': obj.asset_code,
                'adapter_id': obj.adapter_id,
                'adapter_account_id': obj.adapter_account_id,
                'adapter_account_name': (acc.name or f'Account #{obj.adapter_account_id}') if obj.adapter_account_id and acc else None,
                'config': raw_config_masked,
                'effective_config': effective_masked,
                'acquisition_interval_minutes': obj.acquisition_interval_minutes,
                'enabled': obj.enabled,
                'created_at': obj.created_at.isoformat() if obj.created_at else '',
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else '',
            }
            data.append(row)

        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size) if total_count else 0,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_create_asset_adapter_config(request):
    """API endpoint to create AssetAdapterConfig. Admin only. Optional adapter_account_id links to an account (config = overrides only)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.models import AdapterAccount, AssetAdapterConfig

        data = json.loads(request.body)
        asset_code = (data.get('asset_code') or '').strip()
        adapter_id = (data.get('adapter_id') or '').strip()
        adapter_account_id = data.get('adapter_account_id')
        config = data.get('config')
        if config is None:
            config = {}
        if not isinstance(config, dict):
            config = {}
        acquisition_interval = int(data.get('acquisition_interval_minutes', 5))
        enabled = bool(data.get('enabled', True))

        if not asset_code:
            return JsonResponse({'error': 'asset_code is required'}, status=400)
        if not adapter_id:
            return JsonResponse({'error': 'adapter_id is required'}, status=400)
        from data_collection.adapters import get_registered_ids
        registered = set(get_registered_ids() or [])
        if adapter_id not in registered:
            return JsonResponse({'error': f'adapter_id must be a registered adapter (got: {adapter_id})'}, status=400)

        if adapter_account_id is not None:
            try:
                account = AdapterAccount.objects.get(pk=adapter_account_id, enabled=True)
            except AdapterAccount.DoesNotExist:
                return JsonResponse({'error': f'Adapter account {adapter_account_id} not found or disabled'}, status=400)
            if account.adapter_id != adapter_id:
                return JsonResponse({'error': f'Account adapter_id is {account.adapter_id}, must match adapter_id {adapter_id}'}, status=400)
            # Credentials come from account; config is overrides only (e.g. plant_id)
        else:
            if adapter_id == 'fusion_solar':
                base_url = (config.get('api_base_url') or '').strip()
                username = (config.get('username') or '').strip()
                password = (config.get('password') or '').strip()
                if not base_url or not username or not password:
                    return JsonResponse({
                        'error': 'Fusion Solar requires api_base_url, username and password in config (or link to an adapter account)',
                    }, status=400)

        if AssetAdapterConfig.objects.filter(asset_code=asset_code, adapter_id=adapter_id).exists():
            return JsonResponse({'error': f'Config already exists for asset {asset_code} and adapter {adapter_id}'}, status=400)

        obj = AssetAdapterConfig.objects.create(
            asset_code=asset_code,
            adapter_id=adapter_id,
            adapter_account_id=adapter_account_id,
            config=config,
            acquisition_interval_minutes=(
                acquisition_interval if acquisition_interval in (5, 30, 60, 1440) else 5
            ),
            enabled=enabled,
        )
        return JsonResponse({
            'success': True,
            'message': 'Adapter config created successfully!',
            'id': obj.id,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_update_asset_adapter_config(request):
    """API endpoint to update AssetAdapterConfig. Admin only."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.models import AssetAdapterConfig

        data = json.loads(request.body)
        config_id = data.get('id')
        if not config_id:
            return JsonResponse({'error': 'id is required'}, status=400)

        obj = AssetAdapterConfig.objects.get(id=config_id)
        if 'config' in data and isinstance(data['config'], dict):
            new_config = dict(data['config'])
            existing = obj.config or {}
            # Preserve existing api_key if client sent masked value
            if new_config.get('api_key') in ('****', '', None) and existing.get('api_key'):
                new_config['api_key'] = existing['api_key']
            # Preserve existing password for Fusion Solar when client sent masked/empty (only when no adapter_account)
            if obj.adapter_id == 'fusion_solar' and not obj.adapter_account_id and new_config.get('password') in ('****', '', None) and existing.get('password'):
                new_config['password'] = existing['password']
            obj.config = new_config
        if 'adapter_account_id' in data:
            obj.adapter_account_id = data['adapter_account_id'] if data['adapter_account_id'] else None
        if 'acquisition_interval_minutes' in data:
            val = int(data['acquisition_interval_minutes'])
            obj.acquisition_interval_minutes = val if val in (5, 30, 60, 1440) else 5
        if 'enabled' in data:
            obj.enabled = bool(data['enabled'])
        obj.save()

        return JsonResponse({'success': True, 'message': 'Adapter config updated successfully!'})
    except AssetAdapterConfig.DoesNotExist:
        return JsonResponse({'error': 'Config not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@role_required_api(allowed_roles=['admin'])
@login_required
def api_delete_asset_adapter_config(request, config_id):
    """API endpoint to delete AssetAdapterConfig. Superuser only."""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    try:
        from data_collection.models import AssetAdapterConfig

        if not request.user.is_superuser:
            return JsonResponse({'error': 'Only superusers can delete adapter config'}, status=403)

        obj = AssetAdapterConfig.objects.get(id=config_id)
        obj.delete()
        return JsonResponse({'success': True, 'message': 'Adapter config deleted successfully!'})
    except AssetAdapterConfig.DoesNotExist:
        return JsonResponse({'error': 'Config not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# AdapterAccount CRUD (list, create) – for account-centric data collection
@role_required_api(allowed_roles=['admin'])
@login_required
def api_adapter_account_list(request):
    """List adapter accounts (credentials). Optional filter by adapter_id."""
    try:
        from data_collection.models import AdapterAccount

        adapter_id_filter = request.GET.get('adapter_id', '').strip()
        qs = AdapterAccount.objects.all().order_by('adapter_id', 'name', 'id')
        if adapter_id_filter:
            qs = qs.filter(adapter_id=adapter_id_filter)
        accounts = []
        for acc in qs:
            accounts.append({
                'id': acc.id,
                'adapter_id': acc.adapter_id,
                'name': acc.name or '',
                'config': _mask_adapter_config(acc.config or {}, acc.adapter_id),
                'enabled': acc.enabled,
                'created_at': acc.created_at.isoformat() if acc.created_at else '',
                'updated_at': acc.updated_at.isoformat() if acc.updated_at else '',
            })
        return JsonResponse({'data': accounts})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_create_adapter_account(request):
    """Create an adapter account (one credential set). Admin only."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.models import AdapterAccount

        data = json.loads(request.body)
        adapter_id = (data.get('adapter_id') or '').strip()
        name = (data.get('name') or '').strip()
        config = data.get('config')
        if config is None:
            config = {}
        if not isinstance(config, dict):
            config = {}
        enabled = bool(data.get('enabled', True))

        if not adapter_id:
            return JsonResponse({'error': 'adapter_id is required'}, status=400)
        from data_collection.adapters import get_registered_ids
        registered = set(get_registered_ids() or [])
        if adapter_id not in registered:
            return JsonResponse({'error': f'adapter_id must be a registered adapter (got: {adapter_id})'}, status=400)
        if adapter_id == 'fusion_solar':
            base_url = (config.get('api_base_url') or '').strip()
            username = (config.get('username') or '').strip()
            password = (config.get('password') or '').strip()
            if not base_url or not username or not password:
                return JsonResponse({
                    'error': 'Fusion Solar account requires api_base_url, username and password in config',
                }, status=400)
        elif adapter_id == 'laplaceid':
            base_url = (config.get('api_base_url') or '').strip()
            username = (config.get('username') or '').strip()
            password = (config.get('password') or '').strip()
            if not base_url or not username or not password:
                return JsonResponse({
                    'error': 'LaplaceID account requires api_base_url, username and password in config',
                }, status=400)
        elif adapter_id == 'solargis':
            api_url = (config.get('api_url') or '').strip()
            api_key = (config.get('api_key') or config.get('subscription_token') or '').strip()
            if not api_url or not api_key:
                return JsonResponse({
                    'error': 'Solargis account requires api_url and api_key (subscription token) in config',
                }, status=400)

        obj = AdapterAccount.objects.create(
            adapter_id=adapter_id,
            name=name or None,
            config=config,
            enabled=enabled,
        )
        return JsonResponse({'success': True, 'message': 'Adapter account created.', 'id': obj.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_update_adapter_account(request):
    """Update an adapter account (name, enabled, config). Admin only."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.models import AdapterAccount

        data = json.loads(request.body or '{}')
        account_id = data.get('id')
        if not account_id:
            return JsonResponse({'error': 'id is required'}, status=400)

        obj = AdapterAccount.objects.get(id=account_id)
        name = (data.get('name') or '').strip()
        enabled = bool(data.get('enabled', True))
        config = data.get('config')
        if config is None or not isinstance(config, dict):
            config = obj.config or {}
        # Preserve existing secrets when client sends masked/empty values
        existing = obj.config or {}
        if config.get('api_key') in ('', '****', None) and existing.get('api_key'):
            config = dict(config)
            config['api_key'] = existing['api_key']
        if obj.adapter_id in ('fusion_solar', 'laplaceid') and config.get('password') in ('', '****', None) and existing.get('password'):
            config = dict(config) if isinstance(config, dict) else {}
            config['password'] = existing.get('password')
        # Validate credentials when updating Solargis/Fusion Solar account config
        if obj.adapter_id == 'fusion_solar':
            base_url = (config.get('api_base_url') or '').strip()
            username = (config.get('username') or '').strip()
            password = (config.get('password') or '').strip()
            if not base_url or not username or not password:
                return JsonResponse({
                    'error': 'Fusion Solar account requires api_base_url, username and password in config',
                }, status=400)
        elif obj.adapter_id == 'laplaceid':
            base_url = (config.get('api_base_url') or '').strip()
            username = (config.get('username') or '').strip()
            password = (config.get('password') or '').strip()
            if not base_url or not username or not password:
                return JsonResponse({
                    'error': 'LaplaceID account requires api_base_url, username and password in config',
                }, status=400)
        elif obj.adapter_id == 'solargis':
            api_url = (config.get('api_url') or '').strip()
            api_key = (config.get('api_key') or config.get('subscription_token') or '').strip()
            if not api_url or not api_key:
                return JsonResponse({
                    'error': 'Solargis account requires api_url and api_key (subscription token) in config',
                }, status=400)

        if name:
            obj.name = name
        obj.enabled = enabled
        obj.config = dict(config)
        obj.save()

        return JsonResponse({'success': True, 'message': 'Adapter account updated.'})
    except AdapterAccount.DoesNotExist:
        return JsonResponse({'error': 'Account not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@superuser_required
@role_required_api(allowed_roles=['admin'])
@login_required
def api_delete_adapter_account(request, account_id):
    """Delete an adapter account. Superuser only."""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)
    try:
        from data_collection.models import AdapterAccount, AssetAdapterConfig

        if not request.user.is_superuser:
            return JsonResponse({'error': 'Only superusers can delete adapter accounts'}, status=403)

        # Safety: prevent deleting an account that is still referenced by any AssetAdapterConfig
        if AssetAdapterConfig.objects.filter(adapter_account_id=account_id).exists():
            return JsonResponse(
                {
                    'error': 'Cannot delete adapter account while asset adapter configs are still linked to it. '
                             'Please unlink or delete those configs first.'
                },
                status=400,
            )

        obj = AdapterAccount.objects.get(id=account_id)
        obj.delete()
        return JsonResponse({'success': True, 'message': 'Adapter account deleted.'})
    except AdapterAccount.DoesNotExist:
        return JsonResponse({'error': 'Account not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

