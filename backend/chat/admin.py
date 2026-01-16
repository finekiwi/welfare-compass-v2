from django.contrib import admin
from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    """세션 상세 페이지에서 메시지도 같이 보기"""
    model = ChatMessage
    extra = 0
    readonly_fields = ['role', 'content', 'metadata', 'created_at']
    ordering = ['created_at']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'expires_at', 'message_count', 'is_expired_display']
    list_filter = ['created_at']
    search_fields = ['user__username', 'id']
    readonly_fields = ['id', 'created_at']
    inlines = [ChatMessageInline]

    def message_count(self, obj):
        """메시지 개수"""
        return obj.messages.count()
    message_count.short_description = '메시지 수'

    def is_expired_display(self, obj):
        """만료 여부"""
        return '만료됨' if obj.is_expired() else '유효'
    is_expired_display.short_description = '상태'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_short', 'role', 'short_content', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__id']
    readonly_fields = ['created_at']

    def session_short(self, obj):
        """세션 ID 앞 8자리만"""
        return str(obj.session.id)[:8] + '...'
    session_short.short_description = '세션'

    def short_content(self, obj):
        """내용 50자 미리보기"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = '내용'
