from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer,
    ChatSessionDetailSerializer,
    SendMessageSerializer,
    ChatMessageSerializer,
)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    채팅 세션 API
    
    엔드포인트:
    - POST /api/v1/chat/sessions/           : 세션 생성 (+ 웰컴 메시지)
    - GET  /api/v1/chat/sessions/           : 내 세션 목록 (로그인 필요)
    - GET  /api/v1/chat/sessions/{id}/      : 세션 상세 (메시지 포함)
    - POST /api/v1/chat/sessions/{id}/send/ : 메시지 전송 & 응답 받기
    """
    permission_classes = [AllowAny]  # 비로그인도 채팅 가능 (기능명세서)
    lookup_field = 'id'  # UUID 사용

    def get_queryset(self):
        """
        목록(list): 로그인 사용자만 본인 세션 조회
        개별(retrieve, send): 세션 ID 알면 접근 가능 (UUID라서 추측 어려움)
        """
        # 개별 세션 조회/메시지 전송은 모든 사용자 허용 (UUID 보안)
        if self.action in ['retrieve', 'send']:
            return ChatSession.objects.all()
        
        # 목록은 로그인 사용자만
        if self.request.user.is_authenticated:
            return ChatSession.objects.filter(user=self.request.user)
        return ChatSession.objects.none()

    def get_serializer_class(self):
        """retrieve는 상세(메시지 포함), 나머지는 목록용"""
        if self.action == 'retrieve':
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    def create(self, request):
        """
        세션 생성
        
        - 로그인 유저: user 연결
        - 비로그인: user=None
        - 웰컴 메시지 자동 추가
        """
        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None
        )

        # 웰컴 메시지 추가 (프론트 기존 로직과 동일)
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content='안녕하세요! 복지 혜택 찾기를 도와드릴게요. 현재 상황(거주지, 나이, 취업 상태 등)을 말씀해 주시면 맞춤형 정책을 추천해 드릴게요.'
        )

        serializer = ChatSessionDetailSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def send(self, request, id=None):
        """
        메시지 전송 & 응답 받기
        
        흐름:
        1. 사용자 메시지 DB 저장
        2. (TODO) LLM 호출 - Yuna LangGraph 연결
        3. 어시스턴트 응답 DB 저장
        4. 응답 반환
        """
        # 세션 조회
        try:
            session = ChatSession.objects.get(id=id)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': '세션을 찾을 수 없습니다.', 'code': 'SESSION_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 만료 체크 (기능명세서: TTL 30분)
        if session.is_expired():
            return Response(
                {'error': '세션이 만료되었습니다. 새 세션을 시작해주세요.', 'code': 'SESSION_EXPIRED'},
                status=status.HTTP_410_GONE
            )

        # 요청 바디 검증
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_content = serializer.validated_data['content']

        # 1. 사용자 메시지 저장
        user_message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_content
        )

        # =====================================================================
        # 2. TODO: LLM 호출 (Yuna LangGraph 연결)
        # =====================================================================
        # from llm.services.langfuse_client import get_langfuse_handler
        # from llm.agents.graph import welfare_graph
        # 
        # handler = get_langfuse_handler(session_id=str(session.id))
        # result = await welfare_graph.ainvoke(
        #     {"user_query": user_content, "chat_history": session.messages.all()},
        #     config={"callbacks": [handler]}
        # )
        # assistant_content = result["final_response"]
        # metadata = {
        #     "extracted_profile": result.get("extracted_profile"),
        #     "matched_policies": result.get("matched_policies"),
        # }
        # =====================================================================

        # 임시 더미 응답 (LLM 연동 전)
        assistant_content = (
            f"'{user_content[:30]}{'...' if len(user_content) > 30 else ''}'에 대해 분석 중입니다. "
            "현재 테스트 모드로 동작하고 있어요. LLM 연동 후 실제 정책 추천이 제공됩니다. "
            "거주지(구), 나이, 취업 상태 등을 알려주시면 더 정확한 추천이 가능해요."
        )
        metadata = {
            "status": "dummy_response",
            "note": "LLM 연동 전 테스트 응답"
        }

        # 3. 어시스턴트 응답 저장
        assistant_message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=assistant_content,
            metadata=metadata
        )

        # 4. 응답 반환 (프론트 타입에 맞춤: camelCase)
        return Response({
            'userMessage': ChatMessageSerializer(user_message).data,
            'assistantMessage': ChatMessageSerializer(assistant_message).data,
        }, status=status.HTTP_201_CREATED)
