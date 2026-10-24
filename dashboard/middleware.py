import datetime
from django.utils import timezone
from dashboard.models import UserSession

class AnalyticsSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'session') and request.session.session_key:
            session_key = request.session.session_key
            if request.user.is_authenticated:
                # Get or create the active session
                session, created = UserSession.objects.get_or_create(
                    session_key=session_key,
                    defaults={'user': request.user}
                )
                
                # If we have a user now but didn't before, update it
                if not session.user:
                    session.user = request.user
                    session.save(update_fields=['user'])
                
                # Update end_time to now
                now = timezone.now()
                session.end_time = now
                session.duration_seconds = int((now - session.start_time).total_seconds())
                session.save(update_fields=['end_time', 'duration_seconds'])
                
                # Attach session to request for easy access in views
                request.analytics_session = session
            else:
                request.analytics_session = None
        else:
            request.analytics_session = None

        response = self.get_response(request)
        return response
