"""Tests for framework adapters."""

import pytest

from predicate_secure import (
    AdapterError,
    AdapterResult,
    Framework,
    SecureAgent,
    create_adapter,
)


class TestAdapterResult:
    """Tests for AdapterResult dataclass."""

    def test_adapter_result_fields(self):
        """AdapterResult has expected fields."""
        result = AdapterResult(
            agent_runtime=None,
            backend=None,
            tracer=None,
            plugin=None,
            executor="mock_executor",
            metadata={"framework": "test"},
        )
        assert result.executor == "mock_executor"
        assert result.metadata["framework"] == "test"


class TestAdapterError:
    """Tests for AdapterError exception."""

    def test_adapter_error_has_framework(self):
        """AdapterError includes framework info."""
        exc = AdapterError("Test error", Framework.BROWSER_USE)
        assert exc.framework == Framework.BROWSER_USE
        assert "Test error" in str(exc)


class TestCreateAdapter:
    """Tests for create_adapter function."""

    def test_create_adapter_unknown_framework(self):
        """create_adapter raises for unknown framework."""
        with pytest.raises(AdapterError, match="No adapter available"):
            create_adapter(object(), Framework.UNKNOWN)

    def test_create_adapter_pydantic_ai(self):
        """create_adapter works for PydanticAI (no dependencies)."""

        class MockPydanticAgent:
            model = "gpt-4"

        result = create_adapter(MockPydanticAgent(), Framework.PYDANTIC_AI)
        assert result.metadata["framework"] == "pydantic_ai"
        assert result.executor == "gpt-4"


class TestSecureAgentAdapters:
    """Tests for SecureAgent adapter methods."""

    def test_get_adapter_unknown_raises(self):
        """get_adapter raises for unknown frameworks."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        with pytest.raises(AdapterError, match="No adapter available"):
            secure.get_adapter()

    def test_get_browser_use_plugin_wrong_framework(self):
        """get_browser_use_plugin raises for non-browser-use agents."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        with pytest.raises(AdapterError, match="only available for browser-use"):
            secure.get_browser_use_plugin()

    def test_get_langchain_core_wrong_framework(self):
        """get_langchain_core raises for non-LangChain agents."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        with pytest.raises(AdapterError, match="only available for LangChain"):
            secure.get_langchain_core()


class TestBrowserUseAdapterMock:
    """Tests for browser-use adapter with mocks."""

    def test_browser_use_adapter_missing_session(self):
        """browser-use adapter raises if no session found."""

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"
            # No browser or session attribute

        secure = SecureAgent(agent=MockBrowserUseAgent())

        # Should raise because no session found
        # The exact error depends on whether predicate is installed
        with pytest.raises((AdapterError, Exception)):
            secure.get_adapter()

    def test_browser_use_adapter_with_session(self):
        """browser-use adapter detects session attribute."""

        class MockSession:
            pass

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"

            def __init__(self):
                self.browser = MockSession()
                self.llm = "mock_llm"

        secure = SecureAgent(agent=MockBrowserUseAgent())
        assert secure.framework == Framework.BROWSER_USE
        assert secure.wrapped.executor == "mock_llm"


class TestPlaywrightAdapterMock:
    """Tests for Playwright adapter with mocks."""

    def test_playwright_adapter_detection(self):
        """Playwright page is detected correctly."""

        class MockPage:
            __module__ = "playwright.async_api._generated"

        secure = SecureAgent(agent=MockPage())
        assert secure.framework == Framework.PLAYWRIGHT


class TestLangChainAdapterMock:
    """Tests for LangChain adapter with mocks."""

    def test_langchain_adapter_detection(self):
        """LangChain agent is detected correctly."""

        class MockAgentExecutor:
            __module__ = "langchain.agents.executor"

            def __init__(self):
                self.llm = "mock_llm"

        secure = SecureAgent(agent=MockAgentExecutor())
        assert secure.framework == Framework.LANGCHAIN
        assert secure.wrapped.executor == "mock_llm"
