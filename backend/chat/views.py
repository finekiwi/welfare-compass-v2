import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import lru_cache

from django.core import signing
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ChatMessage, ChatSession
from .serializers import (
    ChatMessageSerializer,
    ChatSessionDetailSerializer,
    ChatSessionSerializer,
    SendMessageSerializer,
)

logger = logging.getLogger(__name__)

CHAT_SESSION_TOKEN_HEADER = "X-Chat-Session-Token"
SESSION_TOKEN_SALT = "chat.session.access"
SESSION_TOKEN_MAX_AGE_SECONDS = 30 * 60


def _load_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int env %s=%r. Using default=%s", name, raw, default)
        return default


LLM_TIMEOUT_SECONDS = _load_int_env("CHAT_LLM_TIMEOUT_SECONDS", 25)
LLM_MAX_RETRIES = max(0, _load_int_env("CHAT_LLM_MAX_RETRIES", 1))
_AGENT_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _django_policy_fetcher(policy_ids: list[str] | None) -> list[dict]:
    """Django DB에서 정책 데이터를 가져오는 fetcher (check_eligibility tool용)."""
    from policies.models import Policy

    qs = Policy.objects.all()
    if policy_ids:
        qs = qs.filter(policy_id__in=policy_ids)

    results = []
    for p in qs.iterator():
        results.append({
            "policy_id": p.policy_id,
            "title": p.title,
            "description": p.description or "",
            "support_content": p.support_content or "",
            "age_min": p.age_min,
            "age_max": p.age_max,
            "income_level": p.income_level or "",
            "income_max": p.income_max,
            "district": p.district or "",
            "category": p.category or "",
            "subcategory": p.subcategory or "",
            "employment_status": p.employment_status or "",
            "education_status": p.education_status or "",
            "marriage_status": p.marriage_status or "",
            "apply_start_date": str(p.apply_start_date) if p.apply_start_date else None,
            "apply_end_date": str(p.apply_end_date) if p.apply_end_date else None,
            "apply_url": p.apply_url or "",
            "sbiz_cd": p.sbiz_cd or "",
            "is_for_single_parent": p.is_for_single_parent,
            "is_for_disabled": p.is_for_disabled,
            "is_for_low_income": p.is_for_low_income,
            "is_for_newlywed": p.is_for_newlywed,
        })
    return results


@lru_cache(maxsize=1)
def _get_agent():
    """Thread-safe lazy singleton per process."""
    from langgraph.checkpoint.memory import MemorySaver
    from llm.agents.agent import create_agent

    return create_agent(checkpointer=MemorySaver(), policy_fetcher=_django_policy_fetcher)


def _build_session_token(session_id: str) -> str:
    signer = signing.TimestampSigner(salt=SESSION_TOKEN_SALT)
    return signer.sign(session_id)


def _extract_session_token(request) -> str | None:
    return request.headers.get(CHAT_SESSION_TOKEN_HEADER) or request.query_params.get("sessionToken")


def _is_valid_session_token(session_id: str, token: str | None) -> bool:
    if not token:
        return False

    signer = signing.TimestampSigner(salt=SESSION_TOKEN_SALT)
    try:
        raw_value = signer.unsign(token, max_age=SESSION_TOKEN_MAX_AGE_SECONDS)
    except (signing.BadSignature, signing.SignatureExpired):
        return False

    return raw_value == session_id


def _run_agent_with_timeout_and_retry(user_content: str, thread_id: str) -> dict:
    from llm.agents.agent import run_agent

    last_error: Exception | None = None
    max_attempts = LLM_MAX_RETRIES + 1

    for attempt in range(1, max_attempts + 1):
        future = _AGENT_EXECUTOR.submit(run_agent, _get_agent(), user_content, thread_id)
        try:
            return future.result(timeout=LLM_TIMEOUT_SECONDS)
        except FuturesTimeoutError as exc:
            last_error = exc
            logger.warning(
                "LLM call timed out (session_id=%s, attempt=%s/%s, timeout=%ss)",
                thread_id,
                attempt,
                max_attempts,
                LLM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            last_error = exc
            logger.exception(
                "LLM call failed with exception (session_id=%s, attempt=%s/%s)",
                thread_id,
                attempt,
                max_attempts,
            )
        finally:
            future.cancel()

    if isinstance(last_error, FuturesTimeoutError):
        raise TimeoutError(f"LLM call timed out after {max_attempts} attempts")

    raise RuntimeError("LLM call failed after retries") from last_error


class ChatSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        """
        list: only authenticated user's sessions
        retrieve/send: session lookup with explicit access validation
        """
        if self.action in ["retrieve", "send"]:
            if self.request.user.is_authenticated:
                return ChatSession.objects.filter(user=self.request.user)
            return ChatSession.objects.filter(user__isnull=True)

        if self.request.user.is_authenticated:
            return ChatSession.objects.filter(user=self.request.user)
        return ChatSession.objects.none()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    def _get_session_or_404(self, session_id):
        try:
            return ChatSession.objects.get(id=session_id), None
        except ChatSession.DoesNotExist:
            return None, Response(
                {"error": "Session not found.", "code": "SESSION_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def _authorize_session_access(self, request, session):
        # Authenticated session: owner only.
        if session.user_id is not None:
            if not request.user.is_authenticated or request.user.id != session.user_id:
                return Response(
                    {"error": "Forbidden session access.", "code": "SESSION_FORBIDDEN"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return None

        # Anonymous session: signed token required.
        token = _extract_session_token(request)
        if not _is_valid_session_token(str(session.id), token):
            return Response(
                {"error": "Invalid session token.", "code": "SESSION_FORBIDDEN"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return None

    def create(self, request):
        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None
        )

        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content="안녕하세요! 복지 혜택 찾기를 도와드릴게요. 현재 상황(거주지, 나이, 취업 상태 등)을 말씀해 주시면 맞춤형 정책을 추천해 드릴게요.",
        )

        payload = ChatSessionDetailSerializer(session).data
        if session.user_id is None:
            payload["sessionToken"] = _build_session_token(str(session.id))

        return Response(payload, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        session_id = kwargs.get(self.lookup_field)
        session, error_response = self._get_session_or_404(session_id)
        if error_response:
            return error_response

        forbidden = self._authorize_session_access(request, session)
        if forbidden:
            return forbidden

        serializer = ChatSessionDetailSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def send(self, request, id=None):
        session, error_response = self._get_session_or_404(id)
        if error_response:
            return error_response

        forbidden = self._authorize_session_access(request, session)
        if forbidden:
            return forbidden

        if session.is_expired():
            return Response(
                {
                    "error": "Session expired. Please start a new session.",
                    "code": "SESSION_EXPIRED",
                },
                status=status.HTTP_410_GONE,
            )

        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_content = serializer.validated_data["content"]

        try:
            result = _run_agent_with_timeout_and_retry(
                user_content,
                thread_id=str(session.id),
            )
        except TimeoutError:
            logger.exception("LLM call timeout (session_id=%s)", session.id)
            return Response(
                {
                    "error": "AI response timed out. Please retry.",
                    "code": "LLM_TIMEOUT",
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception:
            logger.exception("LLM call failed (session_id=%s)", session.id)
            return Response(
                {"error": "Failed to generate AI response.", "code": "LLM_ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if result.get("error"):
            logger.error("LLM response error (session_id=%s): %s", session.id, result["error"])
            return Response(
                {"error": result["error"], "code": "LLM_ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        assistant_content = result["response"]
        metadata = {"tool_calls": result.get("tool_calls", [])}

        with transaction.atomic():
            user_message = ChatMessage.objects.create(
                session=session,
                role="user",
                content=user_content,
            )
            assistant_message = ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=assistant_content,
                metadata=metadata,
            )

        return Response(
            {
                "userMessage": ChatMessageSerializer(user_message).data,
                "assistantMessage": ChatMessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )
