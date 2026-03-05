from django.contrib import admin
from django.utils.html import format_html
from .models import Policy, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_id', 'title', 'district', 'apply_end_date', 'poster_preview']
    list_filter = ['categories', 'district']
    search_fields = ['title', 'description']
    readonly_fields = ['poster_image_tag']

    fieldsets = [
        (None, {
            'fields': ['policy_id', 'title', 'description', 'support_content', 'district']
        }),
        ('포스터 이미지', {
            'fields': ['poster', 'poster_image_tag'],
            'description': '정책 전용 포스터 이미지를 업로드합니다. 비워두면 카테고리 기본 이미지가 표시됩니다.',
        }),
    ]

    @admin.display(description='포스터')
    def poster_preview(self, obj):
        if obj.poster:
            return format_html('<img src="{}" style="height:32px; border-radius:4px;" />', obj.poster.url)
        return '-'

    @admin.display(description='이미지 미리보기')
    def poster_image_tag(self, obj):
        if obj.poster:
            return format_html(
                '<img src="{}" style="max-height:200px; border-radius:8px; border:1px solid #ddd;" />',
                obj.poster.url
            )
        return '포스터가 업로드되지 않았습니다.'
