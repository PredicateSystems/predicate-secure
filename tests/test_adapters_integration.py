"""Integration tests for framework adapters.

These tests verify that adapters correctly wire sdk-python components
when the predicate package is available.
"""

import pytest

from predicate_secure import (
    AdapterError,
    AdapterResult,
    Framework,
    SecureAgent,
    create_adapter,
    create_browser_use_adapter,
    create_langchain_adapter,
    create_playwright_adapter,
    create_pydantic_ai_adapter,
)

# Check if predicate is available
try:
    from predicate.integrations.browser_use.plugin import PredicateBrowserUsePlugin

    HAS_BROWSER_USE_ADAPTER = True
except ImportError:
    HAS_BROWSER_USE_ADAPTER = False
    PredicateBrowserUsePlugin = None  # type: ignore[misc,assignment]

try:
    from predicate.agent_runtime import AgentRuntime  # noqa: F401

    HAS_AGENT_RUNTIME = True
except ImportError:
    HAS_AGENT_RUNTIME = False

try:
    from predicate.integrations.langchain.core import SentienceLangChainCore

    HAS_LANGCHAIN_CORE = True
except ImportError:
    HAS_LANGCHAIN_CORE = False


class TestBrowserUseAdapterIntegration:
    """Integration tests for browser-use adapter with real predicate imports."""

    @pytest.mark.skipif(not HAS_BROWSER_USE_ADAPTER, reason="predicate not installed")
    def test_create_browser_use_adapter_returns_plugin(self):
        """create_browser_use_adapter returns PredicateBrowserUsePlugin."""

        class MockSession:
            pass

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"

            def __init__(self):
                self.browser = MockSession()
                self.llm = "mock_llm"

        result = create_browser_use_adapter(MockBrowserUseAgent())

        assert isinstance(result, AdapterResult)
        assert result.plugin is not None
        assert isinstance(result.plugin, PredicateBrowserUsePlugin)
        assert result.executor == "mock_llm"
        assert result.metadata["framework"] == "browser_use"
        assert result.metadata["has_session"] is True

    @pytest.mark.skipif(not HAS_BROWSER_USE_ADAPTER, reason="predicate not installed")
    def test_create_browser_use_adapter_missing_session_raises(self):
        """create_browser_use_adapter raises AdapterError if no session found."""

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"
            # No browser or session attribute

        with pytest.raises(AdapterError, match="Could not find browser session"):
            create_browser_use_adapter(MockBrowserUseAgent())

    @pytest.mark.skipif(not HAS_BROWSER_USE_ADAPTER, reason="predicate not installed")
    def test_secure_agent_get_browser_use_plugin(self):
        """SecureAgent.get_browser_use_plugin() returns working plugin."""

        class MockSession:
            pass

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"

            def __init__(self):
                self.browser = MockSession()
                self.llm = "mock_llm"

        secure = SecureAgent(agent=MockBrowserUseAgent())
        plugin = secure.get_browser_use_plugin()

        assert isinstance(plugin, PredicateBrowserUsePlugin)
        # Plugin should have lifecycle hooks
        assert hasattr(plugin, "on_step_start")
        assert hasattr(plugin, "on_step_end")


class TestPlaywrightAdapterIntegration:
    """Integration tests for Playwright adapter with real predicate imports."""

    @pytest.mark.skipif(not HAS_AGENT_RUNTIME, reason="predicate not installed")
    def test_create_playwright_adapter_returns_runtime(self):
        """create_playwright_adapter returns AgentRuntime with mock page.

        Note: The adapter accepts any page-like object and creates a runtime.
        Full integration testing requires a real Playwright browser session.
        """

        class MockPage:
            __module__ = "playwright.async_api._generated"

        result = create_playwright_adapter(MockPage())

        assert isinstance(result, AdapterResult)
        assert result.agent_runtime is not None
        assert result.metadata["framework"] == "playwright"
        assert result.metadata["has_runtime"] is True

    def test_secure_agent_detects_playwright_framework(self):
        """SecureAgent detects Playwright pages correctly."""

        class MockPage:
            __module__ = "playwright.sync_api._generated"

        secure = SecureAgent(agent=MockPage())
        assert secure.framework == Framework.PLAYWRIGHT
        assert secure.wrapped.metadata.get("is_async") is False


class TestLangChainAdapterIntegration:
    """Integration tests for LangChain adapter with real predicate imports."""

    @pytest.mark.skipif(not HAS_LANGCHAIN_CORE, reason="predicate langchain not installed")
    def test_create_langchain_adapter_without_browser(self):
        """create_langchain_adapter works without browser (limited functionality)."""

        class MockAgentExecutor:
            __module__ = "langchain.agents.executor"

            def __init__(self):
                self.llm = "mock_llm"

        result = create_langchain_adapter(MockAgentExecutor())

        assert isinstance(result, AdapterResult)
        # Without browser, plugin is None
        assert result.plugin is None
        assert result.executor == "mock_llm"
        assert result.metadata["framework"] == "langchain"
        assert result.metadata["has_browser"] is False

    @pytest.mark.skipif(not HAS_LANGCHAIN_CORE, reason="predicate langchain not installed")
    def test_create_langchain_adapter_with_browser(self):
        """create_langchain_adapter returns SentienceLangChainCore with browser."""

        class MockAgentExecutor:
            __module__ = "langchain.agents.executor"

            def __init__(self):
                self.llm = "mock_llm"

        class MockBrowser:
            pass

        result = create_langchain_adapter(MockAgentExecutor(), browser=MockBrowser())

        assert isinstance(result, AdapterResult)
        assert result.plugin is not None
        assert isinstance(result.plugin, SentienceLangChainCore)
        assert result.executor == "mock_llm"
        assert result.metadata["has_browser"] is True

    @pytest.mark.skipif(not HAS_LANGCHAIN_CORE, reason="predicate langchain not installed")
    def test_secure_agent_get_langchain_core_without_browser(self):
        """SecureAgent.get_langchain_core() returns None without browser."""

        class MockAgentExecutor:
            __module__ = "langchain.agents.executor"

            def __init__(self):
                self.llm = "mock_llm"

        secure = SecureAgent(agent=MockAgentExecutor())
        core = secure.get_langchain_core()

        # Without browser, core is None
        assert core is None


class TestPydanticAIAdapterIntegration:
    """Integration tests for PydanticAI adapter."""

    def test_create_pydantic_ai_adapter_extracts_model(self):
        """create_pydantic_ai_adapter extracts model from agent."""

        class MockPydanticAgent:
            __module__ = "pydantic_ai.agent"
            model = "gpt-4-turbo"

        result = create_pydantic_ai_adapter(MockPydanticAgent())

        assert isinstance(result, AdapterResult)
        assert result.executor == "gpt-4-turbo"
        assert result.metadata["framework"] == "pydantic_ai"
        assert result.metadata["model"] == "gpt-4-turbo"

    def test_create_pydantic_ai_adapter_no_model(self):
        """create_pydantic_ai_adapter handles missing model gracefully."""

        class MockPydanticAgent:
            __module__ = "pydantic_ai.agent"
            # No model attribute

        result = create_pydantic_ai_adapter(MockPydanticAgent())

        assert result.executor is None
        assert result.metadata["model"] is None


class TestCreateAdapterDispatch:
    """Tests for create_adapter dispatch logic."""

    def test_create_adapter_dispatches_to_pydantic_ai(self):
        """create_adapter dispatches to correct adapter for PydanticAI."""

        class MockPydanticAgent:
            model = "claude-3"

        result = create_adapter(MockPydanticAgent(), Framework.PYDANTIC_AI)

        assert result.metadata["framework"] == "pydantic_ai"
        assert result.executor == "claude-3"

    def test_create_adapter_unknown_raises_adapter_error(self):
        """create_adapter raises AdapterError for unknown frameworks."""
        with pytest.raises(AdapterError) as exc_info:
            create_adapter(object(), Framework.UNKNOWN)

        assert exc_info.value.framework == Framework.UNKNOWN
        assert "No adapter available" in str(exc_info.value)

    @pytest.mark.skipif(not HAS_BROWSER_USE_ADAPTER, reason="predicate not installed")
    def test_create_adapter_dispatches_to_browser_use(self):
        """create_adapter dispatches to browser-use adapter."""

        class MockSession:
            pass

        class MockBrowserUseAgent:
            def __init__(self):
                self.browser = MockSession()

        result = create_adapter(MockBrowserUseAgent(), Framework.BROWSER_USE)

        assert result.metadata["framework"] == "browser_use"
        assert result.plugin is not None

    @pytest.mark.skipif(not HAS_LANGCHAIN_CORE, reason="predicate langchain not installed")
    def test_create_adapter_dispatches_to_langchain(self):
        """create_adapter dispatches to LangChain adapter."""

        class MockAgentExecutor:
            pass

        result = create_adapter(MockAgentExecutor(), Framework.LANGCHAIN)

        assert result.metadata["framework"] == "langchain"
        # Without browser, plugin is None
        assert result.metadata["has_browser"] is False


class TestSecureAgentAdapterMethods:
    """Tests for SecureAgent adapter convenience methods."""

    def test_get_adapter_with_pydantic_ai(self):
        """SecureAgent.get_adapter() works for PydanticAI."""

        class MockPydanticAgent:
            __module__ = "pydantic_ai.agent"
            model = "gpt-4"

        secure = SecureAgent(agent=MockPydanticAgent())
        adapter = secure.get_adapter()

        assert adapter.metadata["framework"] == "pydantic_ai"
        assert adapter.executor == "gpt-4"

    def test_get_browser_use_plugin_wrong_framework_raises(self):
        """get_browser_use_plugin raises for non-browser-use agents."""

        class MockPlaywrightPage:
            __module__ = "playwright.async_api._generated"

        secure = SecureAgent(agent=MockPlaywrightPage())

        with pytest.raises(AdapterError, match="only available for browser-use"):
            secure.get_browser_use_plugin()

    def test_get_langchain_core_wrong_framework_raises(self):
        """get_langchain_core raises for non-LangChain agents."""

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"

        secure = SecureAgent(agent=MockBrowserUseAgent())

        with pytest.raises(AdapterError, match="only available for LangChain"):
            secure.get_langchain_core()


class TestAdapterResultDataclass:
    """Tests for AdapterResult dataclass behavior."""

    def test_adapter_result_all_fields_none(self):
        """AdapterResult can have all optional fields as None."""
        result = AdapterResult(
            agent_runtime=None,
            backend=None,
            tracer=None,
            plugin=None,
            executor=None,
            metadata={},
        )
        assert result.agent_runtime is None
        assert result.backend is None
        assert result.tracer is None
        assert result.plugin is None
        assert result.executor is None

    def test_adapter_result_with_values(self):
        """AdapterResult stores all provided values."""
        mock_runtime = object()
        mock_backend = object()
        mock_tracer = object()
        mock_plugin = object()
        mock_executor = object()

        result = AdapterResult(
            agent_runtime=mock_runtime,
            backend=mock_backend,
            tracer=mock_tracer,
            plugin=mock_plugin,
            executor=mock_executor,
            metadata={"key": "value"},
        )

        assert result.agent_runtime is mock_runtime
        assert result.backend is mock_backend
        assert result.tracer is mock_tracer
        assert result.plugin is mock_plugin
        assert result.executor is mock_executor
        assert result.metadata == {"key": "value"}


class TestAdapterErrorException:
    """Tests for AdapterError exception behavior."""

    def test_adapter_error_message_and_framework(self):
        """AdapterError includes both message and framework."""
        exc = AdapterError("Failed to create adapter", Framework.BROWSER_USE)

        assert str(exc) == "Failed to create adapter"
        assert exc.framework == Framework.BROWSER_USE

    def test_adapter_error_inherits_from_exception(self):
        """AdapterError is a proper Exception subclass."""
        exc = AdapterError("test", Framework.UNKNOWN)
        assert isinstance(exc, Exception)

    def test_adapter_error_can_be_raised_and_caught(self):
        """AdapterError can be raised and caught."""
        with pytest.raises(AdapterError) as exc_info:
            raise AdapterError("Test error", Framework.PLAYWRIGHT)

        assert "Test error" in str(exc_info.value)
        assert exc_info.value.framework == Framework.PLAYWRIGHT
