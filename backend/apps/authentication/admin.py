from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Tenant, TenantMembership, TenantInvitation
from .org_models import ContextType, Environment

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'role', 'tenant', 'current_tenant', 'is_staff')
    list_filter = ('role', 'tenant', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'tenant__name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Organization', {'fields': ('tenant', 'current_tenant', 'role')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tier', 'created_at')
    list_filter = ('tier',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'joined_at')
    list_filter = ('role', 'tenant')
    search_fields = ('user__email', 'tenant__name')

@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'role', 'status', 'invited_by', 'expires_at')
    list_filter = ('status', 'role', 'tenant')
    search_fields = ('email', 'tenant__name')

@admin.register(ContextType)
class ContextTypeAdmin(admin.ModelAdmin):
    list_display = ('type', 'category', 'tenant', 'created_at')
    list_filter = ('type', 'tenant')
    search_fields = ('type', 'category', 'tenant__name')

@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'slug', 'tenant__name')
    ordering = ('tenant', 'order')
