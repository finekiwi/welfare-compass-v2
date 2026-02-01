from django.contrib import admin
from .models import Policy, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_id', 'title', 'district', 'apply_end_date']  # [RENAME] plcy_no → policy_id, plcy_nm → title, aply_end_dt → apply_end_date
    list_filter = ['categories', 'district']
    search_fields = ['title', 'description']  # [RENAME] plcy_nm → title, plcy_expln_cn → description
