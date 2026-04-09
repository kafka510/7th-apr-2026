"""
Celery tasks for shared app operations
"""
import os
import subprocess
import sys
import logging
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache key prefix for task status
TASK_STATUS_PREFIX = 'export_task_status:'
TASK_FILE_PREFIX = 'export_task_file:'
TASK_ERROR_PREFIX = 'export_task_error:'

# Cache timeout: 1 hour (3600 seconds)
TASK_CACHE_TIMEOUT = 3600


@shared_task(bind=True, max_retries=3)
def export_dashboard_task(
    self,
    task_id: str,
    dashboard_url: str,
    output_path: str,
    format_type: str,
    sessionid: str,
    csrftoken: str,
    active_tab: str = '',
    route_path: str = '',
    filters_json: str = ''
):
    """
    Export dashboard as PNG/PDF using Playwright (async Celery task)
    
    Args:
        task_id: Unique task identifier
        dashboard_url: URL of dashboard to capture
        output_path: Path where file should be saved
        format_type: 'png' or 'pdf'
        sessionid: Session cookie value
        csrftoken: CSRF token cookie value
        active_tab: Active tab ID for SPA
        route_path: Route path for SPA
        filters_json: JSON string with filter data
    """
    try:
        # Update status to processing
        cache_key = f'{TASK_STATUS_PREFIX}{task_id}'
        cache.set(cache_key, 'processing', TASK_CACHE_TIMEOUT)

        logger.info(f"Starting export task {task_id} for URL: {dashboard_url}")

        # Find Python executable
        python_executable = sys.executable

        # Locate Playwright script
        if hasattr(settings, "BASE_DIR"):
            base_dir = str(settings.BASE_DIR)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        script_path = os.path.join(base_dir, "scripts", "capture_dashboard.py")

        if not os.path.exists(script_path):
            error_msg = f"Capture script not found: {script_path}"
            logger.error(error_msg)
            cache.set(
                f'{TASK_STATUS_PREFIX}{task_id}',
                'failed',
                TASK_CACHE_TIMEOUT
            )
            cache.set(
                f'{TASK_ERROR_PREFIX}{task_id}',
                'Screenshot service not configured',
                TASK_CACHE_TIMEOUT
            )
            return

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Run Playwright script
        result = subprocess.run(
            [
                python_executable,
                script_path,
                dashboard_url,
                output_path,
                format_type,
                sessionid,
                csrftoken,
                active_tab,
                route_path,
                filters_json,
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            check=False,  # Don't raise on non-zero exit
        )

        # Check if file was generated
        if not os.path.exists(output_path):
            error_msg = f"Screenshot not generated: {output_path}"
            logger.error(error_msg)
            if result.stderr:
                logger.error(f"Script stderr: {result.stderr}")
            if result.stdout:
                logger.error(f"Script stdout: {result.stdout}")

            cache.set(
                f'{TASK_STATUS_PREFIX}{task_id}',
                'failed',
                TASK_CACHE_TIMEOUT
            )
            cache.set(
                f'{TASK_ERROR_PREFIX}{task_id}',
                'Failed to generate screenshot. Please check server logs.',
                TASK_CACHE_TIMEOUT
            )
            return

        # Success - update status and file path
        # Generate file URL (relative to MEDIA_URL)
        file_url = f"/media/{os.path.basename(output_path)}"

        cache.set(
            f'{TASK_STATUS_PREFIX}{task_id}',
            'completed',
            TASK_CACHE_TIMEOUT
        )
        cache.set(
            f'{TASK_FILE_PREFIX}{task_id}',
            file_url,
            TASK_CACHE_TIMEOUT
        )

        logger.info(f"Export task {task_id} completed successfully: {file_url}")

    except subprocess.TimeoutExpired:
        error_msg = f"Playwright timeout for task {task_id}"
        logger.error(error_msg)
        cache.set(
            f'{TASK_STATUS_PREFIX}{task_id}',
            'failed',
            TASK_CACHE_TIMEOUT
        )
        cache.set(
            f'{TASK_ERROR_PREFIX}{task_id}',
            'Screenshot generation timed out. The page may be taking too long to load.',
            TASK_CACHE_TIMEOUT
        )

    except Exception as e:
        error_msg = f"Unexpected error in export task {task_id}: {str(e)}"
        logger.exception(error_msg)
        cache.set(
            f'{TASK_STATUS_PREFIX}{task_id}',
            'failed',
            TASK_CACHE_TIMEOUT
        )
        cache.set(
            f'{TASK_ERROR_PREFIX}{task_id}',
            f'Unexpected error: {str(e)}',
            TASK_CACHE_TIMEOUT
        )


def get_task_status(task_id: str):
    """Get task status from cache"""
    status = cache.get(f'{TASK_STATUS_PREFIX}{task_id}')
    if status is None:
        return None
    
    result = {
        'status': status,
    }
    
    if status == 'completed':
        file_url = cache.get(f'{TASK_FILE_PREFIX}{task_id}')
        result['file_url'] = file_url
    elif status == 'failed':
        error = cache.get(f'{TASK_ERROR_PREFIX}{task_id}')
        result['error'] = error or 'Export failed'
    
    return result

