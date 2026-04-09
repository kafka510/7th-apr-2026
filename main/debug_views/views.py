from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from main.models import UserProfile, AssetList, YieldData, MapData, BESSData, AOCData, ICEData, MinamataStringLossData, ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData
from django.db import transaction
from django.db.models import Count
import json

@login_required
def debug_user_access(request):
    """Debug view to show user access information"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_role = user_profile.role
        
        # Get total sites available
        total_sites = AssetList.objects.count()
        
        # Get Japan and Korea sites
        japan_sites = AssetList.objects.filter(country='JP').count()
        korea_sites = AssetList.objects.filter(country='KR').count()
        
        # Get user's accessible sites
        accessible_sites = user_profile.get_accessible_sites()
        accessible_site_count = accessible_sites.count()
        
        # Get user's assigned countries, portfolios, and sites
        assigned_countries = user_profile.countries.all()
        assigned_portfolios = user_profile.portfolios.all()
        assigned_sites = user_profile.sites.all()
        
        context = {
            'user_role': user_role,
            'total_sites': total_sites,
            'japan_sites': japan_sites,
            'korea_sites': korea_sites,
            'accessible_site_count': accessible_site_count,
            'assigned_countries': assigned_countries,
            'assigned_portfolios': assigned_portfolios,
            'assigned_sites': assigned_sites,
        }
        
        return render(request, 'debug/debug_user_access.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found')
        return redirect('main:home')

@login_required
def debug_data_visibility(request):
    """Debug view to show data visibility information"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        accessible_sites = user_profile.get_accessible_sites()
        accessible_site_numbers = list(accessible_sites.values_list('asset_number', flat=True))
        
        # Count data for different models
        total_yield_data = YieldData.objects.count()
        accessible_yield_data = YieldData.objects.filter(assetno__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        
        total_map_data = MapData.objects.count()
        accessible_map_data = MapData.objects.filter(asset_no__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        
        total_bess_data = BESSData.objects.count()
        accessible_bess_data = BESSData.objects.filter(asset_no__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        
        total_aoc_data = AOCData.objects.count()
        accessible_aoc_data = AOCData.objects.filter(asset_no__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        
        total_ice_data = ICEData.objects.count()
        accessible_ice_data = ICEData.objects.count()  # ICE data is portfolio-based, not site-based
        
        total_minamata_data = MinamataStringLossData.objects.count()
        accessible_minamata_data = MinamataStringLossData.objects.count()  # This is portfolio-based
        
        # Daily data counts
        total_actual_generation = ActualGenerationDailyData.objects.count()
        accessible_actual_generation = ActualGenerationDailyData.objects.filter(asset_code__in=accessible_sites.values_list('asset_code', flat=True)).count() if accessible_sites.exists() else 0
        
        total_expected_budget = ExpectedBudgetDailyData.objects.count()
        accessible_expected_budget = ExpectedBudgetDailyData.objects.filter(asset_code__in=accessible_sites.values_list('asset_code', flat=True)).count() if accessible_sites.exists() else 0
        
        total_budget_gii = BudgetGIIDailyData.objects.count()
        accessible_budget_gii = BudgetGIIDailyData.objects.filter(asset_code__in=accessible_sites.values_list('asset_code', flat=True)).count() if accessible_sites.exists() else 0
        
        total_actual_gii = ActualGIIDailyData.objects.count()
        accessible_actual_gii = ActualGIIDailyData.objects.filter(asset_code__in=accessible_sites.values_list('asset_code', flat=True)).count() if accessible_sites.exists() else 0
        
        context = {
            'user_role': user_profile.role,
            'accessible_site_numbers': accessible_site_numbers,
            'accessible_site_count': len(accessible_site_numbers),
            'total_yield_data': total_yield_data,
            'accessible_yield_data': accessible_yield_data,
            'total_map_data': total_map_data,
            'accessible_map_data': accessible_map_data,
            'total_bess_data': total_bess_data,
            'accessible_bess_data': accessible_bess_data,
            'total_aoc_data': total_aoc_data,
            'accessible_aoc_data': accessible_aoc_data,
            'total_ice_data': total_ice_data,
            'accessible_ice_data': accessible_ice_data,
            'total_minamata_data': total_minamata_data,
            'accessible_minamata_data': accessible_minamata_data,
            'total_actual_generation': total_actual_generation,
            'accessible_actual_generation': accessible_actual_generation,
            'total_expected_budget': total_expected_budget,
            'accessible_expected_budget': accessible_expected_budget,
            'total_budget_gii': total_budget_gii,
            'accessible_budget_gii': accessible_budget_gii,
            'total_actual_gii': total_actual_gii,
            'accessible_actual_gii': accessible_actual_gii,
        }
        
        return render(request, 'debug/debug_data_visibility.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found')
        return redirect('main:home')

@login_required
def debug_api_endpoints(request):
    """Debug view to test API endpoints and their data filtering"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        accessible_sites = user_profile.get_accessible_sites()
        accessible_site_numbers = list(accessible_sites.values_list('asset_number', flat=True))
        
        context = {
            'user_role': user_profile.role,
            'accessible_site_numbers': accessible_site_numbers,
            'accessible_site_count': len(accessible_site_numbers),
        }
        
        return render(request, 'debug/debug_api_endpoints.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found')
        return redirect('main:home')

@login_required
def debug_asset_assignment(request):
    """Debug view to check asset assignment and AssetList population"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Check AssetList population
        asset_list_count = AssetList.objects.count()
        japan_assets = AssetList.objects.filter(country='JP').count()
        korea_assets = AssetList.objects.filter(country='KR').count()
        
        # Check user's assigned assets
        assigned_countries = user_profile.countries.all()
        assigned_portfolios = user_profile.portfolios.all()
        assigned_sites = user_profile.sites.all()
        
        # Check if AssetList is properly populated
        asset_list_populated = asset_list_count > 0
        
        # Get distinct countries and portfolios from assigned assets
        distinct_countries = set()
        distinct_portfolios = set()
        
        if assigned_countries.exists():
            distinct_countries = set(asset.country for asset in assigned_countries if asset.country)
        
        if assigned_portfolios.exists():
            distinct_portfolios = set(asset.portfolio for asset in assigned_portfolios if asset.portfolio)
        
        context = {
            'user_role': user_profile.role,
            'asset_list_count': asset_list_count,
            'japan_assets': japan_assets,
            'korea_assets': korea_assets,
            'assigned_countries': assigned_countries,
            'assigned_portfolios': assigned_portfolios,
            'assigned_sites': assigned_sites,
            'distinct_countries': distinct_countries,
            'distinct_portfolios': distinct_portfolios,
            'asset_list_populated': asset_list_populated,
        }
        
        return render(request, 'debug/debug_asset_assignment.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found')
        return redirect('main:home')

@login_required
def fix_user_country_assignments(request):
    """Debug view to fix user country assignments through web interface"""
    if request.method == 'POST':
        username = request.POST.get('username')
        action = request.POST.get('action')
        
        if username and action == 'fix':
            try:
                user_profile = UserProfile.objects.get(user__username=username)
                
                with transaction.atomic():
                    # Fix country assignments
                    if user_profile.countries.exists():
                        assigned_assets = user_profile.countries.all()
                        distinct_countries = set(asset.country for asset in assigned_assets if asset.country)
                        
                        if distinct_countries:
                            # Clear current country assignments
                            user_profile.countries.clear()
                            
                            # Get AssetList records for these countries (one per country)
                            country_assets = []
                            for country in distinct_countries:
                                country_asset = AssetList.objects.filter(country=country).first()
                                if country_asset:
                                    country_assets.append(country_asset)
                            
                            # Assign the country representative assets
                            if country_assets:
                                user_profile.countries.set(country_assets)
                                messages.success(request, f'Fixed country assignments for {username}: {len(country_assets)} countries instead of {assigned_assets.count()} individual assets')
                            else:
                                messages.warning(request, f'No valid country assets found for {username}')
                    
                    # Fix portfolio assignments
                    if user_profile.portfolios.exists():
                        assigned_portfolio_assets = user_profile.portfolios.all()
                        distinct_portfolios = set(asset.portfolio for asset in assigned_portfolio_assets if asset.portfolio)
                        
                        if distinct_portfolios:
                            # Clear current portfolio assignments
                            user_profile.portfolios.clear()
                            
                            # Get AssetList records for these portfolios (one per portfolio)
                            portfolio_assets = []
                            for portfolio in distinct_portfolios:
                                portfolio_asset = AssetList.objects.filter(portfolio=portfolio).first()
                                if portfolio_asset:
                                    portfolio_assets.append(portfolio_asset)
                            
                            # Assign the portfolio representative assets
                            if portfolio_assets:
                                user_profile.portfolios.set(portfolio_assets)
                                messages.success(request, f'Fixed portfolio assignments for {username}: {len(portfolio_assets)} portfolios instead of {assigned_portfolio_assets.count()} individual assets')
                            else:
                                messages.warning(request, f'No valid portfolio assets found for {username}')
                
                return redirect('debug:fix_user_country_assignments')
                
            except UserProfile.DoesNotExist:
                messages.error(request, f'User profile not found for username: {username}')
            except Exception as e:
                messages.error(request, f'Error fixing assignments: {str(e)}')
    
    # Get all user profiles for display
    user_profiles = UserProfile.objects.select_related('user').all()
    
    # Analyze each user's assignments
    user_analysis = []
    for user_profile in user_profiles:
        analysis = {
            'username': user_profile.user.username,
            'role': user_profile.role,
            'countries_count': user_profile.countries.count(),
            'portfolios_count': user_profile.portfolios.count(),
            'sites_count': user_profile.sites.count(),
        }
        
        # Check if countries field has individual AssetList records
        if user_profile.countries.exists():
            assigned_assets = user_profile.countries.all()
            distinct_countries = set(asset.country for asset in assigned_assets if asset.country)
            analysis['distinct_countries'] = list(distinct_countries)
            analysis['needs_fixing'] = len(distinct_countries) < assigned_assets.count()
        
        # Check portfolios
        if user_profile.portfolios.exists():
            assigned_portfolio_assets = user_profile.portfolios.all()
            distinct_portfolios = set(asset.portfolio for asset in assigned_portfolio_assets if asset.portfolio)
            analysis['distinct_portfolios'] = list(distinct_portfolios)
            analysis['needs_fixing'] = analysis.get('needs_fixing', False) or len(distinct_portfolios) < assigned_portfolio_assets.count()
        
        user_analysis.append(analysis)
    
    context = {
        'user_analysis': user_analysis,
    }
    
    return render(request, 'debug/fix_user_country_assignments.html', context) 