from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import UserSession, AnalyticsEvent
from django.contrib.auth.models import User
from users.models import Profile
import random
import uuid
import datetime

class Command(BaseCommand):
    help = 'Generates historical analytics data for testing'

    def handle(self, *args, **kwargs):
        users = list(User.objects.filter(is_staff=False, is_superuser=False))
        if not users:
            self.stdout.write(self.style.ERROR('No normal users found. Please create some users first.'))
            return

        self.stdout.write('Clearing existing analytics data...')
        UserSession.objects.all().delete()
        AnalyticsEvent.objects.all().delete()

        now = timezone.now()
        
        # Generate 30 days of data
        days = 30
        
        self.stdout.write(f'Generating {days} days of data...')
        
        events_to_create = []
        sessions_to_create = []

        for day in range(days, -1, -1):
            date = now - datetime.timedelta(days=day)
            
            # Number of active users this day
            num_active = random.randint(min(1, len(users)), min(50, len(users)))
            active_users = random.sample(users, num_active)
            
            for user in active_users:
                # 1 to 3 sessions per user
                for _ in range(random.randint(1, 3)):
                    start_time = date.replace(hour=random.randint(8, 20), minute=random.randint(0, 59))
                    duration = random.randint(60, 1800) # 1 to 30 mins
                    end_time = start_time + datetime.timedelta(seconds=duration)
                    
                    session = UserSession(
                        user=user,
                        session_key=str(uuid.uuid4())[:40],
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration
                    )
                    session.save() # need to save to get ID for events
                    
                    # Generate events for this session
                    # Funnel events
                    events = ['site_visit']
                    if random.random() > 0.3:
                        events.append('signup')
                    if random.random() > 0.4:
                        events.append('template_view')
                    if random.random() > 0.6:
                        events.append('template_edit')
                    if random.random() > 0.8:
                        events.append('poster_export')
                        
                    # Feature events
                    features = ['feature_templates', 'feature_text_edit', 'feature_image_upload', 'feature_export', 'feature_sharing']
                    for feat in features:
                        if random.random() > 0.7:
                            events.append(feat)
                            
                    for i, ev in enumerate(events):
                        ev_time = start_time + datetime.timedelta(seconds=int((i/len(events)) * duration))
                        events_to_create.append(AnalyticsEvent(
                            user=user,
                            session=session,
                            event_type=ev,
                            timestamp=ev_time
                        ))

        AnalyticsEvent.objects.bulk_create(events_to_create)
        self.stdout.write(self.style.SUCCESS('Successfully generated analytics data!'))
