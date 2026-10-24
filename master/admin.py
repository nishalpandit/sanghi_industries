from django.contrib import admin
from .models import BusinessType, BusinessCategory, TemplateCategory, Template, FlexDesign


@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)
    ordering = ('name',)


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)
    ordering = ('name',)


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent_category', 'is_active', 'created_at')
    list_filter = ('is_active', 'parent_category')
    search_fields = ('name',)


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'status', 'usage_count', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('name', 'description')
    readonly_fields = ('usage_count', 'created_at', 'updated_at')


@admin.register(FlexDesign)
class FlexDesignAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'usage_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('usage_count', 'created_at', 'updated_at')

