from rest_framework import serializers
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    메시지 시리얼라이저
    
    프론트 타입(chatbot.types.ts)에 맞춤:
    - id: string (숫자 → 문자열)
    - role: "user" | "assistant"
    - content: string
    - createdAt: number (timestamp milliseconds)
    """
    id = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'createdAt']

    def get_id(self, obj):
        """id를 문자열로 변환 (프론트 타입: string)"""
        return str(obj.id)

    def get_createdAt(self, obj):
        """timestamp를 밀리초로 변환 (프론트 타입: number)"""
        return int(obj.created_at.timestamp() * 1000)


class ChatSessionSerializer(serializers.ModelSerializer):
    """
    세션 시리얼라이저 (목록용)
    
    세션 목록 조회 시 사용 - 메시지 개수, 마지막 메시지 미리보기 포함
    """
    messageCount = serializers.SerializerMethodField()
    lastMessage = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()
    expiresAt = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'createdAt', 'expiresAt', 'messageCount', 'lastMessage']

    def get_createdAt(self, obj):
        return int(obj.created_at.timestamp() * 1000)

    def get_expiresAt(self, obj):
        return int(obj.expires_at.timestamp() * 1000)

    def get_messageCount(self, obj):
        """세션 내 메시지 개수"""
        return obj.messages.count()

    def get_lastMessage(self, obj):
        """마지막 메시지 미리보기"""
        last = obj.messages.last()
        if last:
            return {
                'content': last.content[:50] + '...' if len(last.content) > 50 else last.content,
                'createdAt': int(last.created_at.timestamp() * 1000)
            }
        return None


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    """
    세션 상세 시리얼라이저 (메시지 포함)
    
    세션 상세 조회 시 사용 - 모든 메시지 포함
    """
    messages = ChatMessageSerializer(many=True, read_only=True)
    createdAt = serializers.SerializerMethodField()
    expiresAt = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'createdAt', 'expiresAt', 'messages']

    def get_createdAt(self, obj):
        return int(obj.created_at.timestamp() * 1000)

    def get_expiresAt(self, obj):
        return int(obj.expires_at.timestamp() * 1000)


class SendMessageSerializer(serializers.Serializer):
    """
    메시지 전송 요청용
    
    POST /api/v1/chat/sessions/{id}/send/ 요청 바디 검증
    """
    content = serializers.CharField(max_length=500, help_text='메시지 내용 (최대 500자)')
