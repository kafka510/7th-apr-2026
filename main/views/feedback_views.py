"""
Feedback system views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from django.contrib import messages

from django.conf import settings

from accounts.decorators import feature_required
import logging
import os
from ..models import (
    FeedbackImage, Feedback
)
from ..forms import FeedbackForm
from django.http import HttpResponse
from django.core.paginator import Paginator
from .shared.utilities import *
from .shared.decorators import *


# Feedback Views

@login_required
def feedback_submit_view(request):
    """
    View for users to submit feedback.
    Accessible to all authenticated users.
    """
    from waffle import flag_is_active
    
    # Check if React version should be used
    use_react = flag_is_active(request, 'react_feedback_submit')
    
    if use_react:
        return render(request, 'main/feedback_submit_react.html')
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST, request.FILES)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.user_email = request.user.email
            feedback.save()
            
            # Handle multiple images
            images = request.FILES.getlist('images')
            for image in images:
                if image:  # Check if image is not empty
                    FeedbackImage.objects.create(feedback=feedback, image=image)
            
            messages.success(request, 'Thank you for your feedback! It has been submitted successfully.')
            
            # Check if request is from an iframe (modal)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'iframe' in request.META.get('HTTP_REFERER', ''):
                return JsonResponse({
                    'success': True,
                    'message': 'Thank you for your feedback! It has been submitted successfully.',
                    'close_modal': True
                })
            else:
                return redirect('main:feedback_submit')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackForm()
    
    return render(request, 'main/feedback_submit.html', {'form': form})



@login_required
@feature_required('user_management')  # Only admins can access
@require_http_methods(["GET"])
def api_feedback_list(request):
    """
    API endpoint to provide feedback list data for React frontend.
    """
    from django.db.models import Q
    
    # Start with base queryset
    feedback_list = Feedback.objects.all().select_related('user').prefetch_related('images')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '').strip()
    page_number = int(request.GET.get('page', 1))
    
    # Apply status filter
    if status_filter:
        feedback_list = feedback_list.filter(attended_status=status_filter)
    
    # Apply search filter
    if search_query:
        feedback_list = feedback_list.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user_email__icontains=search_query)
        )
    
    # Order by creation date (newest first)
    feedback_list = feedback_list.order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(feedback_list, 10)  # Show 10 feedback per page
    page_obj = paginator.get_page(page_number)
    
    # Serialize feedback items
    feedback_data = []
    for feedback in page_obj:
        feedback_data.append({
            'id': feedback.id,
            'user': {
                'id': feedback.user.id,
                'username': feedback.user.username,
                'first_name': feedback.user.first_name,
                'last_name': feedback.user.last_name,
                'email': feedback.user.email,
            },
            'user_email': feedback.user_email,
            'subject': feedback.subject,
            'message': feedback.message,
            'attended_status': feedback.attended_status,
            'attended_at': feedback.attended_at.isoformat() if feedback.attended_at else None,
            'created_at': feedback.created_at.isoformat(),
            'image_count': feedback.images.count(),
        })
    
    return JsonResponse({
        'results': feedback_data,
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'page': page_number,
        'total_pages': paginator.num_pages,
    })


@login_required
@feature_required('user_management')  # Only admins can access
def feedback_list_view(request):
    """
    View for admins to see all feedback with filtering and search.
    Only accessible to admin users.
    """
    from waffle import flag_is_active
    
    # Check if React version should be used
    use_react = flag_is_active(request, 'react_feedback_list')
    
    if use_react:
        return render(request, 'main/feedback_list_react.html', {
            'is_superuser': request.user.is_superuser,
        })
    
    from django.db.models import Q
    
    # Start with base queryset
    feedback_list = Feedback.objects.all().select_related('user')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '').strip()
    
    # Apply status filter
    if status_filter:
        feedback_list = feedback_list.filter(attended_status=status_filter)
    
    # Apply search filter
    if search_query:
        feedback_list = feedback_list.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user_email__icontains=search_query)
        )
    
    # Order by creation date (newest first)
    feedback_list = feedback_list.order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(feedback_list, 10)  # Show 10 feedback per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare context with filter values for template
    context = {
        'page_obj': page_obj,
        'feedback_list': page_obj,
        'current_status': status_filter,
        'current_search': search_query,
        'total_count': paginator.count,
        'filtered_count': len(page_obj) if page_obj else 0,
    }
    
    return render(request, 'main/feedback_list.html', context)


@login_required
@feature_required('user_management')  # Only admins can access
def mark_feedback_attended(request, feedback_id):
    """
    Mark feedback as attended and send thank you email to the user.
    Only accessible to admin users.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        # Check if already attended
        if feedback.attended_status == 'attended':
            return JsonResponse({
                'success': False,
                'message': 'This feedback has already been marked as attended.'
            })
        
        # Get admin response text from request body
        import json
        admin_response = ''
        try:
            data = json.loads(request.body)
            admin_response = data.get('admin_response', '').strip()
        except (json.JSONDecodeError, AttributeError):
            # If no JSON data, admin_response remains empty
            pass
        
        # Update feedback status
        from django.utils import timezone
        feedback.attended_status = 'attended'
        feedback.attended_at = timezone.now()
        feedback.save()
        
        # Send thank you email
        try:
            from django.template.loader import render_to_string
            from django.core.mail import EmailMultiAlternatives
            
            # Prepare email context
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            context = {
                'user_name': feedback.user.get_full_name() or feedback.user.username,
                'feedback_subject': feedback.subject,
                'feedback_date': feedback.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'admin_response': admin_response,
                'has_admin_response': bool(admin_response),
                'logo_url': f"{site_url}/static/PEAK_LOGO.jpg",
            }
            
            # Render email templates
            html_content = render_to_string('main/feedback_thank_you_email.html', context)
            text_content = render_to_string('main/feedback_thank_you_email.txt', context)
            
            # Create email
            subject = f'Thank You for Your Feedback - {feedback.subject}'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [feedback.user_email]
            
            # Create email message
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            
            email_sent = True
            email_message = "Thank you email sent successfully."
            
        except Exception as e:
            # Log email error but don't fail the entire operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send thank you email for feedback {feedback_id}: {str(e)}")
            email_sent = False
            email_message = f"Feedback marked as attended, but email sending failed: {str(e)}"
        
        return JsonResponse({
            'success': True,
            'message': f'Feedback marked as attended successfully! {email_message}',
            'email_sent': email_sent,
            'attended_at': feedback.attended_at.strftime('%B %d, %Y at %I:%M %p'),
            'subject': feedback.subject
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Add this new view after the mark_feedback_attended view
@login_required
@superuser_required  # Only superusers can delete feedback
def delete_feedback(request, feedback_id):
    """
    Delete feedback entry. Only superusers can delete attended feedback.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
    
    try:
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        # Only allow deletion of attended feedback
        if feedback.attended_status != 'attended':
            return JsonResponse({
                'success': False,
                'message': 'Only attended feedback can be deleted.'
            }, status=400)
        
        # Store feedback info for logging
        user_info = f"{feedback.user.username} ({feedback.user_email})"
        subject = feedback.subject
        created_date = feedback.created_at.strftime('%Y-%m-%d %H:%M')
        
        # Delete associated images first (they will be deleted automatically due to CASCADE)
        # but we can log the count for audit purposes
        image_count = feedback.images.count()
        
        # Delete the feedback
        feedback.delete()
        
        # Log the deletion
        logger = logging.getLogger(__name__)
        logger.info(f"Feedback deleted by superuser {request.user.username}: "
                   f"ID={feedback_id}, User={user_info}, Subject='{subject}', "
                   f"Created={created_date}, Images deleted={image_count}")
        
        return JsonResponse({
            'success': True,
            'message': f'Feedback "{subject}" has been successfully deleted.'
        })
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting feedback {feedback_id}: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while deleting the feedback.'
        }, status=500)


# Add a new AJAX endpoint for loading images
@login_required
@feature_required('user_management')
def feedback_images_ajax(request, feedback_id):
    """
    AJAX endpoint to load images for a specific feedback entry
    """
    feedback = get_object_or_404(Feedback, id=feedback_id)
    images = feedback.images.all()
    
    images_data = []
    for image in images:
        images_data.append({
            'id': image.id,
            'url': image.image.url,
            'name': image.image.name
        })
    
    return JsonResponse({
        'success': True,
        'images': images_data,
        'count': images.count()
    })


@login_required
@feature_required('user_management')  # Only admins can access
def feedback_image_download(request, feedback_id):
    """
    View for admins to download feedback images.
    Only accessible to admin users.
    """
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    if not feedback.image:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No image attached to this feedback.'}, status=404)
        messages.error(request, 'No image attached to this feedback.')
        return redirect('main:feedback_list')
    
    try:
        # Check if file exists
        if not feedback.image.storage.exists(feedback.image.name):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Image file not found on server.'}, status=404)
            messages.error(request, 'Image file not found on server.')
            return redirect('main:feedback_list')
        
        # For iframe context, provide a direct link to the media file
        if 'iframe' in request.GET or 'embed' in request.GET:
            # Redirect to direct media URL
            media_url = f"{settings.MEDIA_URL}{feedback.image.name}"
            return redirect(media_url)
        
        # Open the file and read its content
        with feedback.image.open('rb') as f:
            file_content = f.read()
        
        # Determine content type based on file extension
        import mimetypes
        content_type, _ = mimetypes.guess_type(feedback.image.name)
        if not content_type:
            content_type = 'application/octet-stream'
        
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(feedback.image.name)}"'
        
        # Remove blocking headers for downloads
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Allow downloads from same origin
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = 'GET'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': f'Error downloading image: {str(e)}'}, status=500)
        messages.error(request, f'Error downloading image: {str(e)}')
        return redirect('main:feedback_list')



@login_required
@feature_required('user_management')  # Only admins can access
def feedback_image_direct(request, feedback_id):
    """
    Direct image serving view for downloads without security headers.
    Only accessible to admin users.
    """
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    if not feedback.image:
        return HttpResponse('No image found', status=404)
    
    try:
        # Check if file exists
        if not feedback.image.storage.exists(feedback.image.name):
            return HttpResponse('Image file not found', status=404)
        
        # Open the file and read its content
        with feedback.image.open('rb') as f:
            file_content = f.read()
        
        # Determine content type based on file extension
        import mimetypes
        content_type, _ = mimetypes.guess_type(feedback.image.name)
        if not content_type:
            content_type = 'image/jpeg'  # Default to image
        
        # Create a simple response with minimal headers
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(feedback.image.name)}"'
        response['Content-Length'] = len(file_content)
        
        # Only essential headers - no security restrictions
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

