"""
LangFuse CallbackHandler 연동 테스트

- handler 생성 정상 (환경변수 있을 때)
- handler None 반환 (환경변수 없을 때)
- agent 실행 시 callback 포함 확인 (mock)
- handler 실패해도 agent 정상 실행 (graceful)
"""
from unittest.mock import MagicMock, patch


# ============================================================================
# get_langfuse_handler 단위 테스트
# ============================================================================


def test_handler_returns_none_when_env_missing(monkeypatch):
    """환경변수 없으면 None 반환."""
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)

    from llm.services.langfuse_client import get_langfuse_handler

    assert get_langfuse_handler() is None


def test_handler_returns_none_when_only_secret_key(monkeypatch):
    """LANGFUSE_PUBLIC_KEY 없으면 None 반환."""
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)

    from llm.services.langfuse_client import get_langfuse_handler

    assert get_langfuse_handler() is None


def test_handler_returns_none_when_only_public_key(monkeypatch):
    """LANGFUSE_SECRET_KEY 없으면 None 반환."""
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")

    from llm.services.langfuse_client import get_langfuse_handler

    assert get_langfuse_handler() is None


def test_handler_created_when_env_present(monkeypatch):
    """환경변수 있을 때 handler 정상 생성 (v4: 인자 없이 CallbackHandler() 호출)."""
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

    mock_handler = MagicMock()
    mock_callback_cls = MagicMock(return_value=mock_handler)

    with patch.dict("sys.modules", {"langfuse": MagicMock(), "langfuse.langchain": MagicMock(CallbackHandler=mock_callback_cls)}):
        from importlib import reload
        import llm.services.langfuse_client as module
        reload(module)

        result = module.get_langfuse_handler()

    # v4: session_id/user_id는 langfuse_session()으로 전파, CallbackHandler()는 인자 없이 호출
    mock_callback_cls.assert_called_once_with()
    assert result is mock_handler


def test_handler_returns_none_on_import_failure(monkeypatch):
    """langfuse 임포트 실패 시 None 반환 (graceful degradation)."""
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

    with patch.dict("sys.modules", {"langfuse": None, "langfuse.langchain": None}):
        from importlib import reload
        import llm.services.langfuse_client as module
        reload(module)

        result = module.get_langfuse_handler()

    assert result is None


# ============================================================================
# run_agent callback 연동 테스트
# ============================================================================


def test_run_agent_includes_langfuse_callback(monkeypatch):
    """run_agent 실행 시 LangFuse handler가 config['callbacks']에 포함된다."""
    mock_handler = MagicMock()

    with patch("llm.agents.agent.get_langfuse_handler", return_value=mock_handler) as mock_get:
        mock_agent = MagicMock()
        mock_agent._max_iterations = 3
        mock_agent.invoke.return_value = {
            "messages": [
                MagicMock(type="ai", content='{"message": "테스트", "policies": [], "follow_up": null}')
            ]
        }

        from llm.agents.agent import run_agent
        run_agent(mock_agent, "테스트 메시지", thread_id="thread-42")

    mock_get.assert_called_once_with()
    call_config = mock_agent.invoke.call_args[1]["config"]
    assert mock_handler in call_config["callbacks"]


def test_run_agent_no_callback_when_handler_none(monkeypatch):
    """handler가 None이면 config에 'callbacks' 키가 없다."""
    with patch("llm.agents.agent.get_langfuse_handler", return_value=None):
        mock_agent = MagicMock()
        mock_agent._max_iterations = 3
        mock_agent.invoke.return_value = {
            "messages": [
                MagicMock(type="ai", content='{"message": "응답", "policies": [], "follow_up": null}')
            ]
        }

        from llm.agents.agent import run_agent
        run_agent(mock_agent, "테스트", thread_id="thread-99")

    call_config = mock_agent.invoke.call_args[1]["config"]
    assert "callbacks" not in call_config


def test_run_agent_proceeds_when_handler_returns_none():
    """handler가 None 반환해도 agent 실행은 정상 진행."""
    with patch("llm.agents.agent.get_langfuse_handler", return_value=None):
        mock_agent = MagicMock()
        mock_agent._max_iterations = 3
        mock_agent.invoke.return_value = {
            "messages": [
                MagicMock(type="ai", content="응답")
            ]
        }

        from llm.agents.agent import run_agent
        result = run_agent(mock_agent, "테스트")

    assert result["error"] is None


# ============================================================================
# stream_agent callback 연동 테스트
# ============================================================================


def test_stream_agent_includes_langfuse_callback():
    """stream_agent 실행 시 LangFuse handler가 config['callbacks']에 포함된다."""
    mock_handler = MagicMock()

    with patch("llm.agents.agent.get_langfuse_handler", return_value=mock_handler) as mock_get:
        mock_agent = MagicMock()
        mock_agent.stream.return_value = iter([{"messages": []}])

        from llm.agents.agent import stream_agent
        list(stream_agent(mock_agent, "테스트", thread_id="stream-thread-1"))

    mock_get.assert_called_once_with()
    call_config = mock_agent.stream.call_args[1]["config"]
    assert mock_handler in call_config["callbacks"]


def test_stream_agent_no_callback_when_handler_none():
    """stream_agent에서 handler가 None이면 config에 'callbacks' 키가 없다."""
    with patch("llm.agents.agent.get_langfuse_handler", return_value=None):
        mock_agent = MagicMock()
        mock_agent.stream.return_value = iter([{"messages": []}])

        from llm.agents.agent import stream_agent
        list(stream_agent(mock_agent, "테스트", thread_id="stream-thread-2"))

    call_config = mock_agent.stream.call_args[1]["config"]
    assert "callbacks" not in call_config
