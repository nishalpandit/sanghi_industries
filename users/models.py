import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from master.models import BusinessType, BusinessCategory, City


class Profile(models.Model):
    """Extended user profile linked to Django's built-in User model."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile_number = models.CharField(max_length=15, unique=True, db_index=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    business_name = models.CharField(max_length=255, blank=True, default='')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    business_category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
    )
    business_types = models.ManyToManyField(
        BusinessType,
        blank=True,
        related_name='user_profiles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.mobile_number})'


class OTPRecord(models.Model):
    """Stores OTP records for login and registration verification."""
    PURPOSE_CHOICES = [
        ('login', 'Login'),
        ('register', 'Register'),
    ]

    mobile_number = models.CharField(max_length=15, db_index=True)
    otp_hash = models.CharField(max_length=128, help_text='Hashed OTP value')
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    failed_attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'OTP Record'
        verbose_name_plural = 'OTP Records'

    def __str__(self):
        return f'OTP for {self.mobile_number} ({self.purpose})'


class RegistrationToken(models.Model):
    """Temporary token issued after OTP verification for new user registration."""
    mobile_number = models.CharField(max_length=15, db_index=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Registration Token'
        verbose_name_plural = 'Registration Tokens'

    def __str__(self):
        return f'RegToken for {self.mobile_number}'


class BrandKit(models.Model):
    """Stores the brand kit for a user profile, including logo, colors, and contact info."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='brand_kits')
    name = models.CharField(max_length=100, default='My Brand Kit')
    logo = models.ImageField(upload_to='brand_logos/', null=True, blank=True)
    brand_colors = models.JSONField(default=list, blank=True, help_text='List of hex color codes')
    phone_number = models.CharField(max_length=15, blank=True, default='')
    website = models.URLField(blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Brand Kit'
        verbose_name_plural = 'Brand Kits'

    def __str__(self):
        return f'Brand Kit for {self.profile.user.get_full_name() or self.profile.mobile_number}'


class Subscription(models.Model):
    """Stores subscription details for a user profile."""
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='subscription')
    plan_name = models.CharField(max_length=100, default='Free')
    end_date = models.DateTimeField(null=True, blank=True)
    credits_available = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f'Subscription for {self.profile.user.username} - {self.plan_name}'

    @property
    def days_left(self):
        if self.end_date:
            delta = self.end_date - timezone.now()
            return max(0, delta.days)
        return 0

    @property
    def is_expired(self):
        # A subscription without an end date is considered non-expiring
        if not self.end_date:
            return False
        return self.days_left == 0


@receiver(post_save, sender=Profile)
def create_user_subscription(sender, instance, created, **kwargs):
    if created:
        Subscription.objects.create(profile=instance)


class Transaction(models.Model):
    """Records of subscription purchases."""
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    TYPE_CHOICES = [
        ('subscription', 'Subscription'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('refund', 'Refund'),
    ]
    
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='transactions')
    plan_name = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='subscription')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    payment_method = models.CharField(max_length=50, default='api')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        
    def __str__(self):
        return f'{self.transaction_id} - {self.profile.user.username} - {self.amount}'


class GeneratedPoster(models.Model):
    """Stores references to posters/banners generated by users."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='generated_posters')
    image = models.ImageField(upload_to='generated_posters/')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

        verbose_name = 'Generated Poster'
        verbose_name_plural = 'Generated Posters'

    def __str__(self):
        return f'Poster by {self.profile.user.username} at {self.created_at}'
