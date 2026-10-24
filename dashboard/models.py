from django.db import models
from django.contrib.auth.models import User

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, db_index=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-start_time']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"Session {self.session_key} ({self.user})"

class AnalyticsEvent(models.Model):
    EVENT_TYPES = [
        ('site_visit', 'Site Visit'),
        ('signup', 'Sign Up'),
        ('template_view', 'Template View'),
        ('template_edit', 'Template Edit'),
        ('poster_export', 'Poster Export'),
        ('feature_templates', 'Feature: Templates'),
        ('feature_text_edit', 'Feature: Text Edit'),
        ('feature_image_upload', 'Feature: Image Upload'),
        ('feature_export', 'Feature: Export'),
        ('feature_sharing', 'Feature: Sharing'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(UserSession, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Analytics Event'
        verbose_name_plural = 'Analytics Events'

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"
