"""
PV Device Hierarchy Views
Provides hierarchical filtering for PV device configuration
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from main.models import device_list, AssetList
import logging

logger = logging.getLogger(__name__)


@login_required
def api_get_pv_hierarchy(request):
    """
    Get hierarchical device structure for filtering
    
    Query params:
        - asset_code: Filter by asset
        - inverter_id: Filter by inverter (returns JBs or strings under it)
        - jb_id: Filter by JB (returns strings under it)
    
    Returns:
        Hierarchical structure of devices
    """
    try:
        asset_code = request.GET.get('asset_code')
        inverter_id = request.GET.get('inverter_id')
        jb_id = request.GET.get('jb_id')
        
        result = {}
        
        # Level 1: Get Assets with string devices (ordered alphabetically)
        if not asset_code:
            assets = device_list.objects.filter(
                device_type__icontains='string'
            ).values_list('parent_code', flat=True).distinct().order_by('parent_code')
            
            assets_data = []
            for asset in assets:
                if asset:
                    # Get asset details from asset_list
                    try:
                        asset_obj = AssetList.objects.get(asset_code=asset)
                        assets_data.append({
                            'asset_code': asset,
                            'asset_name': asset_obj.asset_name,
                            'country': asset_obj.country,
                        })
                    except AssetList.DoesNotExist:
                        assets_data.append({
                            'asset_code': asset,
                            'asset_name': asset,
                            'country': None,
                        })
            
            # Sort alphabetically by asset_name
            assets_data.sort(key=lambda x: x['asset_name'])
            
            result['assets'] = assets_data
            return JsonResponse(result)
        
        # Level 2: Get Inverters under selected Asset
        if asset_code and not inverter_id:
            # Find all inverter devices (device_type contains '_inv')
            devices = device_list.objects.filter(
                parent_code=asset_code,
                device_type__icontains='_inv'
            ).order_by('device_id')
            
            inverters = []
            for inv in devices:
                inverters.append({
                    'device_id': inv.device_id,
                    'device_name': inv.device_name,
                    'device_sub_group': inv.device_sub_group,
                })
            
            result['inverters'] = inverters
            
            # Check if JBs exist under this asset
            has_jbs = device_list.objects.filter(
                parent_code=asset_code,
                device_type='jb'
            ).exists()
            
            logger.info(f"JBs exist in asset {asset_code}: {has_jbs}")
            
            result['has_jbs'] = has_jbs
            return JsonResponse(result)
        
        # Level 3: Get JBs under selected Inverter (if JBs exist)
        if asset_code and inverter_id and not jb_id:
            # JBs have device_sub_group = inverter's device_id
            try:
                # Find JBs whose device_sub_group equals the inverter's device_id
                jbs = device_list.objects.filter(
                    parent_code=asset_code,
                    device_type='jb',
                    device_sub_group=inverter_id
                ).order_by('device_id')
                
                logger.info(f"Looking for JBs with device_sub_group={inverter_id}, found: {jbs.count()}")
                
                jbs_data = []
                for jb in jbs:
                    jbs_data.append({
                        'device_id': jb.device_id,
                        'device_name': jb.device_name,
                        'device_sub_group': jb.device_sub_group,
                    })
                
                result['jbs'] = jbs_data
                
                # If no JBs found, return strings directly under inverter
                if not jbs_data:
                    # Strings have device_sub_group = inverter's device_id
                    strings = device_list.objects.filter(
                        parent_code=asset_code,
                        device_type__icontains='string',
                        device_sub_group=inverter_id
                    ).order_by('device_id')[:100]  # Limit for performance
                    
                    logger.info(f"No JBs found, looking for strings with device_sub_group={inverter_id}, found: {strings.count()}")
                    
                    strings_data = []
                    for string in strings:
                        strings_data.append({
                            'device_id': string.device_id,
                            'device_name': string.device_name,
                            'device_sub_group': string.device_sub_group,
                            'module_datasheet_id': string.module_datasheet_id,
                            'modules_in_series': string.modules_in_series,
                        })
                    
                    result['strings'] = strings_data
                
                return JsonResponse(result)
                
            except Exception as e:
                logger.error(f"Error fetching JBs/strings for inverter {inverter_id}: {str(e)}")
                return JsonResponse({'error': str(e)}, status=500)
        
        # Level 4: Get Strings under selected JB
        if asset_code and jb_id:
            try:
                # Strings have device_sub_group = JB's device_id
                strings = device_list.objects.filter(
                    parent_code=asset_code,
                    device_type__icontains='string',
                    device_sub_group=jb_id
                ).order_by('device_id')[:100]  # Limit for performance
                
                logger.info(f"Looking for strings with device_sub_group={jb_id}, found: {strings.count()}")
                
                strings_data = []
                for string in strings:
                    strings_data.append({
                        'device_id': string.device_id,
                        'device_name': string.device_name,
                        'device_sub_group': string.device_sub_group,
                        'module_datasheet_id': string.module_datasheet_id,
                        'modules_in_series': string.modules_in_series,
                    })
                
                result['strings'] = strings_data
                return JsonResponse(result)
                
            except Exception as e:
                logger.error(f"Error fetching strings for JB {jb_id}: {str(e)}")
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in api_get_pv_hierarchy: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': str(e)
        }, status=500)

