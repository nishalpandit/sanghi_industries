from django.db import models


class BusinessType(models.Model):
    """Master table for business types (e.g., Manufacturer, Retailer)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Business Type'
        verbose_name_plural = 'Business Types'

    def __str__(self):
        return self.name


class BusinessCategory(models.Model):
    """Master table for business categories (e.g., Technology, Healthcare)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Business Category'
        verbose_name_plural = 'Business Categories'

    def __str__(self):
        return self.name


class City(models.Model):
    """Master table for cities."""
    name = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'City'
        verbose_name_plural = 'Cities'

    def __str__(self):
        return self.name


class TemplateCategory(models.Model):
    """Master table for template categories (e.g., Festival, Business)."""
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='template_categories/', blank=True, null=True, help_text='Category thumbnail image')
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Template Category'
        verbose_name_plural = 'Template Categories'

    def __str__(self):
        return self.name


class Template(models.Model):
    """Stores individual poster templates and their design files."""
    STATUS_CHOICES = [
        ('published', 'Published'),
        ('draft', 'Draft'),
    ]

    name = models.CharField(max_length=255)
    category = models.ForeignKey(TemplateCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='templates')
    description = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='templates/', help_text='Upload PNG, JPG, or SVG')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Template'
        verbose_name_plural = 'Templates'

    def __str__(self):
        return self.name


class TrendingTemplate(models.Model):
    """Stores trending templates with just name and image."""
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='trending_templates/', help_text='Upload PNG, JPG, or SVG')
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trending Template'
        verbose_name_plural = 'Trending Templates'

    def __str__(self):
        return self.name


class FlexDesign(models.Model):
    """Stores flex designs with just name and image."""
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='flex_designs/', help_text='Upload PNG, JPG, or SVG')
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Flex Design'
        verbose_name_plural = 'Flex Designs'

    def __str__(self):
        return self.name


class Feedback(models.Model):
    """Stores user feedback."""
    CATEGORY_CHOICES = [
        ('Ui / Design', 'Ui / Design'),
        ('Templates', 'Templates'),
        ('Performance', 'Performance'),
        ('Bug report', 'Bug report'),
        ('Feature Request', 'Feature Request'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback')
    rating = models.PositiveSmallIntegerField(help_text="Rating from 1 to 5")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(help_text="Tell us more")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f"{self.category} - {self.rating} Stars by {self.user.username if self.user else 'Anonymous'}"


class SubscriptionPlan(models.Model):
    """Master table for subscription plans."""
    name = models.CharField(max_length=100, unique=True)
    features = models.JSONField(default=list, blank=True, help_text="List of features")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_days = models.PositiveIntegerField(default=30, help_text="Duration in days")
    credits = models.PositiveIntegerField(default=0, help_text="Number of credits allowed")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.name} - ${self.price}"
