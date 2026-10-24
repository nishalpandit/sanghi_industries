from django.contrib import admin
from .models import Profile, OTPRecord, RegistrationToken, BrandKit, Subscription


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'mobile_number', 'business_name', 'business_category', 'created_at')
    search_fields = ('mobile_number', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('business_category',)
    raw_id_fields = ('user',)
    filter_horizontal = ('business_types',)


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'mobile_number', 'purpose', 'is_used', 'failed_attempts', 'expires_at', 'created_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('mobile_number',)
    readonly_fields = ('otp_hash', 'created_at')


@admin.register(RegistrationToken)
class RegistrationTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'mobile_number', 'token', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('mobile_number',)
    readonly_fields = ('token', 'created_at')


@admin.register(BrandKit)
class BrandKitAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'profile', 'phone_number', 'email', 'updated_at')
    search_fields = ('name', 'profile__user__first_name', 'profile__mobile_number', 'phone_number', 'email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'plan_name', 'credits_available', 'end_date', 'is_active')
    search_fields = ('profile__user__username', 'profile__mobile_number', 'plan_name')
    list_filter = ('is_active', 'plan_name')
    readonly_fields = ('created_at', 'updated_at')
