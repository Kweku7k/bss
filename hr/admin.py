from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User  # Import your custom User model

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Add your custom fields to the fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Additional Info'), {'fields': ('staffno', 'approval', 'is_admin')}),
    )

    # Fields to display in the admin user list
    list_display = ('username', 'email', 'staffno', 'approval', 'is_admin', 'is_staff')
    search_fields = ('username', 'email', 'staffno')  # Add search functionality
    list_filter = ('approval', 'is_admin', 'is_staff', 'is_superuser', 'groups')
