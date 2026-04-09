"""
ViewSet for Data Upload endpoints (React app).
Reuses existing logic from main.views.data_upload_views
"""
import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from shared_app.permissions.base_permissions import HasFeaturePermission
from ..serializers.data_upload_serializers import (
    DataCountsSerializer,
    UploadHistoryResponseSerializer,
    DataPreviewResponseSerializer,
    DeleteDataRequestSerializer,
    DeleteDataResponseSerializer,
)


class HasDataUploadAccess(HasFeaturePermission):
    required_feature = 'data_upload'


class DataUploadViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasDataUploadAccess]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @action(detail=False, methods=['get'], url_path='data-counts')
    def data_counts(self, request):
        """Get data counts for all data types"""
        try:
            # Lazy import to avoid circular dependency
            from main.models import (
                YieldData, BESSData, BESSV1Data, AOCData, ICEData, ICVSEXVSCURData,
                MapData, MinamataStringLossData, ActualGenerationDailyData,
                ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
                ICApprovedBudgetDailyData
            )
            
            counts = {
                'yield_count': YieldData.objects.count(),
                'bess_count': BESSData.objects.count(),
                'bess_v1_count': BESSV1Data.objects.count(),
                'aoc_count': AOCData.objects.count(),
                'ice_count': ICEData.objects.count(),
                'icvsexvscur_count': ICVSEXVSCURData.objects.count(),
                'map_count': MapData.objects.count(),
                'minamata_count': MinamataStringLossData.objects.count(),
                'actual_generation_daily_count': ActualGenerationDailyData.objects.count(),
                'expected_budget_daily_count': ExpectedBudgetDailyData.objects.count(),
                'budget_gii_daily_count': BudgetGIIDailyData.objects.count(),
                'actual_gii_daily_count': ActualGIIDailyData.objects.count(),
                'ic_approved_budget_daily_count': ICApprovedBudgetDailyData.objects.count(),
            }
            serializer = DataCountsSerializer(counts)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='upload-history')
    def upload_history(self, request):
        """Get upload history"""
        try:
            from main.models import DataImportLog
            
            if request.user.is_superuser:
                uploads = DataImportLog.objects.all()[:50]
            else:
                uploads = DataImportLog.objects.filter(imported_by=request.user)[:50]
            
            uploads_data = []
            for upload in uploads:
                try:
                    data_type = getattr(upload, 'data_type', 'unknown')
                    if data_type == 'unknown':
                        if 'yield' in upload.file_name.lower():
                            data_type = 'yield'
                        elif 'bessv1' in upload.file_name.lower() or 'bess_v1' in upload.file_name.lower():
                            data_type = 'bess_v1'
                        elif 'bess' in upload.file_name.lower():
                            data_type = 'bess'
                        elif 'aoc' in upload.file_name.lower():
                            data_type = 'aoc'
                        else:
                            data_type = 'unknown'
                    
                    uploads_data.append({
                        'file_name': upload.file_name,
                        'data_type': data_type,
                        'upload_mode': getattr(upload, 'upload_mode', 'append'),
                        'import_date': getattr(upload, 'import_date', None),
                        'records_imported': getattr(upload, 'records_imported', 0),
                        'records_skipped': getattr(upload, 'records_skipped', 0),
                        'status': getattr(upload, 'status', 'success'),
                        'imported_by': getattr(upload.imported_by, 'username', 'Unknown') if hasattr(upload, 'imported_by') and upload.imported_by else 'Unknown',
                        'file_size_mb': getattr(upload, 'file_size_mb', 0),
                        'processing_time': round(getattr(upload, 'processing_time', 0), 2) if getattr(upload, 'processing_time', None) else None,
                        'success_rate': getattr(upload, 'success_rate', 0)
                    })
                except Exception:
                    continue
            
            response_data = {'uploads': uploads_data}
            if not uploads_data:
                response_data['message'] = 'No upload history available yet. Upload some data to see history here.'
            
            serializer = UploadHistoryResponseSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'uploads': [], 'message': 'Unable to load upload history. Please try again later.'},
                status=status.HTTP_200_OK  # Return 200 with empty list instead of error
            )

    @action(detail=False, methods=['get'], url_path='data-preview')
    def data_preview(self, request):
        """Preview data for a specific data type"""
        try:
            data_type = request.query_params.get('data_type')
            if not data_type:
                return Response(
                    {'error': 'data_type parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from main.models import (
                YieldData, BESSData, BESSV1Data, AOCData, ICEData,
                MapData, MinamataStringLossData, ActualGenerationDailyData,
                ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData
            )
            
            model_mapping = {
                'yield': YieldData,
                'bess': BESSData,
                'bess_v1': BESSV1Data,
                'aoc': AOCData,
                'ice': ICEData,
                'map': MapData,
                'minamata': MinamataStringLossData,
                'actual_generation_daily': ActualGenerationDailyData,
                'expected_budget_daily': ExpectedBudgetDailyData,
                'budget_gii_daily': BudgetGIIDailyData,
                'actual_gii_daily': ActualGIIDailyData
            }
            
            model = model_mapping.get(data_type)
            if not model:
                return Response(
                    {'error': 'Invalid data type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            records = model.objects.all()[:10]
            data = []
            for record in records:
                record_data = {}
                for field in model._meta.fields:
                    value = getattr(record, field.name)
                    if hasattr(value, 'isoformat'):
                        record_data[field.name] = value.isoformat()
                    else:
                        record_data[field.name] = str(value) if value is not None else ''
                data.append(record_data)
            
            serializer = DataPreviewResponseSerializer({'data': data})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='upload-csv')
    def upload_csv(self, request):
        """Upload CSV file"""
        try:
            # Reuse existing logic from data_upload_views
            from main.views.data_upload_views import process_csv_upload
            
            if 'csv_file' not in request.FILES:
                return Response(
                    {'error': 'No file uploaded'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = request.FILES['csv_file']
            data_type = request.data.get('data_type', 'unknown')
            upload_mode = request.data.get('upload_mode', 'append')
            
            result = process_csv_upload(
                csv_file=file,
                data_type=data_type,
                upload_mode=upload_mode,
                user=request.user
            )
            
            if result.get('success', False):
                return Response(result, status=status.HTTP_200_OK)
            else:
                # Return complete error details including validation information
                error_response = {
                    'success': False,
                    'error': result.get('error', 'Upload failed'),
                }
                
                # Include validation details if available
                if 'validation_details' in result:
                    error_response['validation_details'] = result['validation_details']
                
                # Include other useful information
                if 'warnings' in result:
                    error_response['warnings'] = result['warnings']
                if 'column_issues' in result:
                    error_response['column_issues'] = result['column_issues']
                if 'data_issues' in result:
                    error_response['data_issues'] = result['data_issues']
                
                return Response(
                    error_response,
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            import traceback
            
            error_response = {
                'success': False,
                'error': str(e),
            }
            
            # In development, include stack trace for debugging
            # Check if DEBUG is enabled
            from django.conf import settings
            if settings.DEBUG:
                error_response['traceback'] = traceback.format_exc()
                error_response['exception_type'] = type(e).__name__
            
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='delete-data')
    def delete_data(self, request):
        """Delete data"""
        try:
            from datetime import datetime
            from main.models import (
                YieldData, BESSData, BESSV1Data, AOCData, ICEData, ICVSEXVSCURData,
                MapData, MinamataStringLossData, ActualGenerationDailyData,
                ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
                ICApprovedBudgetDailyData, LossCalculationData
            )
            from main.views.data_upload_views import delete_data_by_date_range
            
            serializer = DeleteDataRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = serializer.validated_data
            data_type = data['data_type']
            delete_option = data['delete_option']
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            model_mapping = {
                'yield': YieldData,
                'bess': BESSData,
                'bess_v1': BESSV1Data,
                'aoc': AOCData,
                'ice': ICEData,
                'icvsexvscur': ICVSEXVSCURData,
                'map': MapData,
                'minamata': MinamataStringLossData,
                'loss_calculation': LossCalculationData,
                'actual_generation_daily': ActualGenerationDailyData,
                'expected_budget_daily': ExpectedBudgetDailyData,
                'budget_gii_daily': BudgetGIIDailyData,
                'actual_gii_daily': ActualGIIDailyData,
                'ic_approved_budget_daily': ICApprovedBudgetDailyData
            }
            
            model = model_mapping.get(data_type)
            if not model:
                return Response(
                    {'success': False, 'error': 'Invalid data type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if delete_option == 'all':
                deleted_count = model.objects.all().delete()[0]
            elif delete_option == 'date_range':
                if not start_date or not end_date:
                    return Response(
                        {'success': False, 'error': 'Start and end dates are required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                result = delete_data_by_date_range(data_type, str(start_date), str(end_date))
                if not result['success']:
                    return Response(
                        {'success': False, 'error': result['error']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                deleted_count = result['deleted_count']
            else:
                return Response(
                    {'success': False, 'error': 'Invalid delete option'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Successfully deleted {deleted_count} records'
            }
            response_serializer = DeleteDataResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='download')
    def download_data(self, request):
        """Download data as CSV or Excel"""
        try:
            data_type = request.query_params.get('data_type')
            if not data_type:
                from django.http import HttpResponse
                html_content = '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Error</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        h3 { color: #d32f2f; }
                    </style>
                </head>
                <body>
                    <h3>Error</h3>
                    <p>data_type parameter is required</p>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
                </html>
                '''
                return HttpResponse(html_content, content_type='text/html', status=400)
            
            # Check permissions
            from shared_app.permissions.permissions import user_has_capability
            if not user_has_capability(request.user, 'data_upload.manage'):
                from django.http import HttpResponse
                html_content = '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Access Denied</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        h3 { color: #d32f2f; }
                    </style>
                </head>
                <body>
                    <h3>Access Denied</h3>
                    <p>Administrator privileges required to download data.</p>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
                </html>
                '''
                return HttpResponse(html_content, content_type='text/html', status=403)
            
            # Reuse existing download logic
            from main.views.download_views import download_data_view
            
            # The download view returns HttpResponse directly, which DRF can handle
            return download_data_view(request, data_type)
            
        except Exception as e:
            from django.http import HttpResponse
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    h3 {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <h3>Error</h3>
                <p>{str(e)}</p>
                <script>setTimeout(() => window.close(), 3000);</script>
            </body>
            </html>
            '''
            return HttpResponse(html_content, content_type='text/html', status=500)

