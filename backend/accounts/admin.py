from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'birth_year', 'district', 'income_level', 'job_status', 'created_at']
    list_filter = ['district', 'income_level', 'job_status', 'education_status', 'marriage_status']
    search_fields = ['user__username', 'user__email', 'district']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['interests']
