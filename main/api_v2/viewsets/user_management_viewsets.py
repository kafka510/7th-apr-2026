"""
ViewSet for User Management API v2.
Reuses existing logic from main.views.user_management_views.
"""
import json

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.conf import settings

from shared_app.permissions.base_permissions import HasFeaturePermission


class HasUserManagementAccess(HasFeaturePermission):
    """
    Feature-based access for user management pages.
    """

    required_feature = "user_management"


class UserManagementViewSet(viewsets.ViewSet):
    """
    Standardized v2 endpoints for the User Management React app.

    These wrap the existing Django views so that business logic and
    permission checks remain in one place.
    """

    permission_classes = [IsAuthenticated, HasUserManagementAccess]

    @action(detail=False, methods=["get"], url_path="data")
    def data(self, request):
        """
        Wrap `api_user_management_data` into:
            GET /api/v2/main/user-management/data/
        """
        try:
            from main.views.user_management_views import api_user_management_data

            response = api_user_management_data(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode("utf-8"))
                return Response(data, status=response.status_code)
            return response
        except Exception as exc:  # pragma: no cover - defensive
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="activity")
    def activity(self, request):
        """
        Wrap `user_activity_api` into:
            GET /api/v2/main/user-management/activity/
        """
        try:
            from main.views.user_management_views import user_activity_api

            response = user_activity_api(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode("utf-8"))
                return Response(data, status=response.status_code)
            return response
        except Exception as exc:  # pragma: no cover
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], url_path="create")
    def create_user(self, request):
        """
        Create a new user via JSON API:
            POST /api/v2/main/user-management/create/
        """
        try:
            from django.contrib.auth.models import User
            from django.db import transaction
            from main.models import UserProfile
            from main.permissions import APP_ACCESS_LABELS, user_has_capability
            from api.models import APIUser

            # Check permissions
            if not user_has_capability(request.user, 'user_management.manage'):
                return Response(
                    {"error": "Permission denied. Only admin users can create users."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Parse JSON data
            data = request.data
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', '').strip()
            
            # Access control
            access_control = data.get('access_control', [])
            if isinstance(access_control, str):
                access_control = [access_control]
            
            selected_apps = []
            if 'web_access' in access_control or 'web' in access_control:
                selected_apps.append('web')
            if 'ticketing_access' in access_control or 'ticketing' in access_control:
                selected_apps.append('ticketing')
            if 'api_access' in access_control or 'api' in access_control:
                selected_apps.append('api')
            
            web_access = 'web' in selected_apps
            api_access = 'api' in selected_apps
            
            country_names = data.get('countries', [])
            portfolio_names = data.get('portfolios', [])
            site_ids = data.get('sites', [])
            
            # Convert to lists if strings
            if isinstance(country_names, str):
                country_names = [country_names] if country_names else []
            if isinstance(portfolio_names, str):
                portfolio_names = [portfolio_names] if portfolio_names else []
            if isinstance(site_ids, str):
                site_ids = [site_ids] if site_ids else []

            # Validation
            if not username or not email or not password or not role:
                return Response(
                    {"error": "All fields are required (username, email, password, role)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if User.objects.filter(username=username).exists():
                return Response(
                    {"error": "Username already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if User.objects.filter(email=email).exists():
                return Response(
                    {"error": "Email already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user and profile
            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    
                    profile = UserProfile.objects.create(
                        user=user,
                        role=role,
                        created_by=request.user
                    )
                    profile.set_app_access(selected_apps)
                    
                    # Apply hierarchical access control logic
                    if site_ids and site_ids != ['']:
                        profile.accessible_sites = ','.join(site_ids)
                        profile.accessible_countries = ''
                        profile.accessible_portfolios = ''
                    elif portfolio_names and portfolio_names != ['']:
                        profile.accessible_portfolios = ','.join(portfolio_names)
                        profile.accessible_sites = ''
                        profile.accessible_countries = ''
                    elif country_names and country_names != ['']:
                        profile.accessible_countries = ','.join(country_names)
                        profile.accessible_sites = ''
                        profile.accessible_portfolios = ''
                    else:
                        profile.accessible_sites = ''
                        profile.accessible_countries = ''
                        profile.accessible_portfolios = ''
                    
                    profile.save()
                    
                    # Create or update APIUser if API access is granted
                    if api_access:
                        if web_access and api_access:
                            access_level = 'both'
                        elif api_access:
                            access_level = 'api_only'
                        else:
                            access_level = 'web_only'
                        
                        APIUser.objects.update_or_create(
                            user=user,
                            defaults={
                                'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                                'description': f"User created via user management",
                                'access_level': access_level,
                                'status': 'active'
                            }
                        )
                    else:
                        APIUser.objects.filter(user=user).delete()
                    
                    # Build access summary
                    access_parts = [APP_ACCESS_LABELS.get(key, key.title()) for key in selected_apps]
                    access_summary = ', '.join(access_parts) if access_parts else 'No access'
                    
                    return Response({
                        'success': True,
                        'message': f'User {username} created successfully with {access_summary} access!',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'role': role,
                            'app_access': selected_apps,
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                # Cleanup if user was created but profile creation failed
                if 'user' in locals() and user and user.pk:
                    try:
                        user.delete()
                    except:
                        pass
                raise e
                
        except Exception as exc:
            import traceback
            error_msg = str(exc)
            if settings.DEBUG:
                error_msg += f"\nTraceback: {traceback.format_exc()}"
            return Response(
                {"error": f"Error creating user: {error_msg}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )