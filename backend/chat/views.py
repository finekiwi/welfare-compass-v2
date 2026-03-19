import json as _json
import logging
import os
from datetime import date as _date
from functools import lru_cache

from django.core import signing
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ChatMessage, ChatSession
from llm.agents.agent import clear_user_info
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
LLM_RUNTIME_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
    ImportError,
)


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



@lru_cache(maxsize=1)
def _get_agent():
    """Thread-safe lazy singleton per process."""
    from langgraph.checkpoint.memory import MemorySaver
    from llm.agents.agent import create_agent

    return create_agent(
        checkpointer=MemorySaver(),
        policy_fetcher=_fetch_policies_for_agent,
    )


def _fetch_policies_for_agent(policy_ids: list[str] | None) -> list[dict]:
    from policies.models import Policy

    queryset = Policy.objects.all()
    if policy_ids:
        queryset = queryset.filter(policy_id__in=policy_ids)

    return list(
        queryset.values(
            "policy_id",
            "title",
            "category",
            "description",
            "support_content",
            "apply_url",
            "detail_url",
            "apply_end_date",
            "age_min",
            "age_max",
            "income_level",
            "income_max",
            "district",
        )
    )


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


def _run_agent_with_timeout_and_retry(user_content: str, thread_id: str, max_iterations: int | None = None) -> dict:
    from llm.agents.agent import run_agent

    max_attempts = LLM_MAX_RETRIES + 1
    for attempt in range(1, max_attempts + 1):
        result = run_agent(_get_agent(), user_content, thread_id, max_iterations=max_iterations)
        error = result.get("error")
        if not error:
            return result

        if _is_timeout_error(error) and attempt < max_attempts:
            logger.warning(
                "LLM call timed out (session_id=%s, attempt=%s/%s, timeout=%ss). Retrying.",
                thread_id,
                attempt,
                max_attempts,
                LLM_TIMEOUT_SECONDS,
            )
            continue

        return result


def _is_timeout_error(error_message: str | None) -> bool:
    if not error_message:
        return False
    lowered = error_message.lower()
    return (
        "timed out" in lowered
        or "timeout" in lowered
        or "time out" in lowered
    )


class ChatSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        """
        list: only authenticated user's sessions
        """
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

        # 로그인 + 프로필 데이터 있는 사용자 판별
        has_profile_data = False
        if request.user.is_authenticated and hasattr(request.user, "profile"):
            p = request.user.profile
            has_profile_data = bool(p.district or p.birth_year or p.job_status)

        if has_profile_data:
            greeting = (
                "안녕하세요! 복지 혜택 찾기를 도와드릴게요. "
                "현재 상황(거주지, 나이, 취업 상태 등)을 말씀해 주시면 맞춤형 정책을 추천해 드릴게요. "
                "프로필 정보를 반영하면 더 정확한 맞춤 추천이 가능해요."
            )
        else:
            greeting = (
                "안녕하세요! 복지 혜택 찾기를 도와드릴게요. "
                "현재 상황(거주지, 나이, 취업 상태 등)을 말씀해 주시면 맞춤형 정책을 추천해 드릴게요."
            )

        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=greeting,
        )

        payload = ChatSessionDetailSerializer(session).data
        payload["hasProfileData"] = has_profile_data
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
            clear_user_info(str(session.id))
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
        llm_user_content = user_content
        include_profile = serializer.validated_data.get("include_profile", False)

        # 프로필 정보 주입
        if include_profile and request.user.is_authenticated and hasattr(request.user, "profile"):
            profile = request.user.profile
            parts = []
            if profile.district:
                parts.append(f"거주지: {profile.district}")
            if profile.age:
                parts.append(f"나이: 만 {profile.age}세")
            if profile.job_status:
                parts.append(f"취업상태: {profile.get_job_status_display()}")
            if profile.housing_type:
                parts.append(f"주거형태: {profile.get_housing_type_display()}")
            if profile.income_level:
                parts.append(f"소득수준: {profile.get_income_level_display()}")
            if profile.education_status:
                parts.append(f"학력: {profile.get_education_status_display()}")
            if profile.marriage_status:
                parts.append(f"결혼: {profile.get_marriage_status_display()}")
            if profile.has_children:
                ages = profile.children_ages or []
                parts.append(f"자녀: {len(ages)}명 (나이: {', '.join(map(str, ages))})" if ages else "자녀: 있음")
            if profile.special_conditions:
                parts.append(f"특수조건: {', '.join(profile.special_conditions)}")
            if profile.needs:
                parts.append(f"관심분야: {', '.join(profile.needs)}")

            if parts:
                profile_context = "[사용자 프로필 정보] " + ", ".join(parts)
                llm_user_content = f"{profile_context}\n\n{user_content}"

        turn_count = ChatMessage.objects.filter(session=session, role="user").count()
        dynamic_max_iterations = min(5 + turn_count, 10)

        try:
            result = _run_agent_with_timeout_and_retry(
                llm_user_content,
                thread_id=str(session.id),
                max_iterations=dynamic_max_iterations,
            )
        except LLM_RUNTIME_EXCEPTIONS:
            logger.exception("LLM call failed (session_id=%s)", session.id)
            return Response(
                {"error": "Failed to generate AI response.", "code": "LLM_ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if result.get("error"):
            if _is_timeout_error(result["error"]):
                logger.warning("LLM call timeout (session_id=%s): %s", session.id, result["error"])
                return Response(
                    {
                        "error": "AI response timed out. Please retry.",
                        "code": "LLM_TIMEOUT",
                    },
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            logger.error("LLM response error (session_id=%s): %s", session.id, result["error"])
            return Response(
                {"error": result["error"], "code": "LLM_ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        chat_response = result["response"]
        assistant_content = chat_response.message
        response_policies = []
        for policy in getattr(chat_response, "policies", []) or []:
            if hasattr(policy, "to_dict"):
                response_policies.append(policy.to_dict())
            elif isinstance(policy, dict):
                response_policies.append(policy)

        # LLM이 structured policies를 비워 보낸 경우, check_eligibility ToolMessage에서 복구한다.
        if not response_policies:
            eligibility_results: list[dict] = []
            for msg in result.get("messages", []):
                if getattr(msg, "type", "") == "tool" and getattr(msg, "name", "") == "check_eligibility":
                    try:
                        parsed = _json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                        if isinstance(parsed, list):
                            eligibility_results.extend(parsed)
                    except (_json.JSONDecodeError, ValueError, TypeError):
                        continue

            eligible = [p for p in eligibility_results if p.get("is_eligible") is True]
            uncertain = [p for p in eligibility_results if p.get("is_eligible") is None]
            candidates = eligible + uncertain

            if candidates:
                policy_ids = [p.get("policy_id") for p in candidates if p.get("policy_id")]
                db_map = {p["policy_id"]: p for p in _fetch_policies_for_agent(policy_ids)}
                today = _date.today()
                for item in candidates:
                    policy_id = item.get("policy_id", "")
                    db = db_map.get(policy_id, {})
                    deadline_str = db.get("apply_end_date")
                    dday = None
                    if deadline_str:
                        try:
                            dday = (_date.fromisoformat(str(deadline_str)) - today).days
                        except (ValueError, TypeError):
                            dday = None

                    response_policies.append(
                        {
                            "plcy_no": policy_id,
                            "plcy_nm": item.get("title") or db.get("title", ""),
                            "category": db.get("category", ""),
                            "summary": db.get("description") or db.get("support_content", ""),
                            "eligibility": "eligible" if item.get("is_eligible") is True else "uncertain",
                            "ineligible_reasons": item.get("reasons", []),
                            "deadline": str(deadline_str) if deadline_str else None,
                            "dday": dday,
                            "apply_url": db.get("apply_url"),
                            "detail_url": db.get("detail_url"),
                        }
                    )

        metadata = {
            "tool_calls": result.get("tool_calls", []),
            "policies": response_policies,
        }

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
