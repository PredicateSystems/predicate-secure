"""Tests for SecureAgent."""

import pytest

from predicate_secure import (
    MODE_AUDIT,
    MODE_DEBUG,
    MODE_PERMISSIVE,
    MODE_STRICT,
    AuthorizationDenied,
    DetectionResult,
    Framework,
    FrameworkDetector,
    PolicyLoadError,
    SecureAgent,
    SecureAgentConfig,
    UnsupportedFrameworkError,
    VerificationFailed,
    WrappedAgent,
)


class TestSecureAgentInit:
    """Tests for SecureAgent initialization."""

    def test_init_with_defaults(self):
        """SecureAgent can be initialized with minimal args."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        assert secure._agent is mock_agent
        assert secure._mode == MODE_STRICT

    def test_init_with_policy_path(self):
        """SecureAgent accepts policy path."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent, policy="policies/test.yaml")
        assert secure._policy == "policies/test.yaml"

    def test_init_with_mode(self):
        """SecureAgent accepts different modes."""
        mock_agent = object()
        for mode in [MODE_STRICT, MODE_PERMISSIVE, MODE_DEBUG, MODE_AUDIT]:
            secure = SecureAgent(agent=mock_agent, mode=mode)
            assert secure._mode == mode

    def test_attach_factory_method(self):
        """SecureAgent.attach() creates instance."""
        mock_agent = object()
        secure = SecureAgent.attach(mock_agent, mode=MODE_DEBUG)
        assert isinstance(secure, SecureAgent)
        assert secure._agent is mock_agent
        assert secure._mode == MODE_DEBUG

    def test_config_property(self):
        """SecureAgent exposes config property."""
        mock_agent = object()
        secure = SecureAgent(
            agent=mock_agent,
            policy="test.yaml",
            mode=MODE_PERMISSIVE,
            principal_id="test:agent",
        )
        assert isinstance(secure.config, SecureAgentConfig)
        assert secure.config.mode == "permissive"
        assert secure.config.effective_principal_id == "test:agent"
        assert secure.config.effective_policy_path == "test.yaml"

    def test_wrapped_property(self):
        """SecureAgent exposes wrapped property."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        assert isinstance(secure.wrapped, WrappedAgent)
        assert secure.wrapped.original is mock_agent
        assert secure.wrapped.framework == "unknown"

    def test_framework_property(self):
        """SecureAgent exposes framework property."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        assert secure.framework == Framework.UNKNOWN

    def test_repr(self):
        """SecureAgent has useful repr."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent, policy="test.yaml", mode=MODE_DEBUG)
        repr_str = repr(secure)
        assert "SecureAgent" in repr_str
        assert "unknown" in repr_str
        assert "debug" in repr_str
        assert "test.yaml" in repr_str


class TestSecureAgentConfig:
    """Tests for SecureAgentConfig."""

    def test_defaults(self):
        """Config has sensible defaults."""
        config = SecureAgentConfig()
        assert config.mode == "strict"
        assert config.fail_closed is True
        assert config.mandate_ttl_seconds == 300

    def test_from_kwargs(self):
        """Config can be created from kwargs."""
        config = SecureAgentConfig.from_kwargs(
            policy="test.yaml",
            mode="permissive",
            principal_id="test:agent",
        )
        assert config.effective_policy_path == "test.yaml"
        assert config.mode == "permissive"
        assert config.fail_closed is False
        assert config.effective_principal_id == "test:agent"

    def test_from_kwargs_invalid_mode(self):
        """Config raises on invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            SecureAgentConfig.from_kwargs(mode="invalid")

    def test_effective_principal_id_fallback(self):
        """Config falls back to default principal."""
        config = SecureAgentConfig()
        assert config.effective_principal_id == "agent:default"

    def test_fail_closed_by_mode(self):
        """fail_closed depends on mode."""
        assert SecureAgentConfig(mode="strict").fail_closed is True
        assert SecureAgentConfig(mode="permissive").fail_closed is False
        assert SecureAgentConfig(mode="debug").fail_closed is False
        assert SecureAgentConfig(mode="audit").fail_closed is False


class TestFrameworkDetector:
    """Tests for framework detection."""

    def test_detect_unknown(self):
        """Unknown objects detected as UNKNOWN."""
        result = FrameworkDetector.detect(object())
        assert result.framework == Framework.UNKNOWN
        assert result.confidence == 0.0

    def test_detect_by_module(self):
        """Objects detected by module name."""

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"

        result = FrameworkDetector.detect(MockBrowserUseAgent())
        assert result.framework == Framework.BROWSER_USE
        assert result.confidence == 1.0

    def test_detect_playwright_page(self):
        """Playwright pages detected by attributes."""

        class MockPage:
            __module__ = "some.module"

            def goto(self):
                pass

            def click(self):
                pass

            def evaluate(self):
                pass

        result = FrameworkDetector.detect(MockPage())
        assert result.framework == Framework.PLAYWRIGHT
        assert result.confidence == 0.7

    def test_detection_result_immutable(self):
        """DetectionResult is immutable."""
        result = DetectionResult(
            framework=Framework.BROWSER_USE,
            agent_type="Agent",
            confidence=1.0,
            metadata={},
        )
        with pytest.raises(Exception):  # frozen dataclass
            result.confidence = 0.5


class TestWrappedAgent:
    """Tests for WrappedAgent."""

    def test_wrapped_agent_fields(self):
        """WrappedAgent has expected fields."""
        original = object()
        wrapped = WrappedAgent(
            original=original,
            framework="browser_use",
            agent_runtime=None,
            executor=None,
            metadata={"key": "value"},
        )
        assert wrapped.original is original
        assert wrapped.framework == "browser_use"
        assert wrapped.metadata == {"key": "value"}


class TestExceptions:
    """Tests for custom exceptions."""

    def test_authorization_denied(self):
        """AuthorizationDenied is an Exception."""
        with pytest.raises(AuthorizationDenied):
            raise AuthorizationDenied("Action denied by policy")

    def test_authorization_denied_with_decision(self):
        """AuthorizationDenied can include decision."""
        decision = {"allowed": False, "reason": "policy"}
        exc = AuthorizationDenied("denied", decision=decision)
        assert exc.decision == decision

    def test_verification_failed(self):
        """VerificationFailed is an Exception."""
        with pytest.raises(VerificationFailed):
            raise VerificationFailed("Post-execution check failed")

    def test_verification_failed_with_predicate(self):
        """VerificationFailed can include predicate."""
        exc = VerificationFailed("failed", predicate="url_matches('example.com')")
        assert exc.predicate == "url_matches('example.com')"

    def test_policy_load_error(self):
        """PolicyLoadError is an Exception."""
        with pytest.raises(PolicyLoadError):
            raise PolicyLoadError("Invalid policy file")

    def test_unsupported_framework_error(self):
        """UnsupportedFrameworkError includes detection info."""
        detection = DetectionResult(
            framework=Framework.UNKNOWN,
            agent_type="CustomAgent",
            confidence=0.0,
            metadata={"module": "custom.module"},
        )
        exc = UnsupportedFrameworkError(detection)
        assert exc.detection is detection
        assert "CustomAgent" in str(exc)
        assert "custom.module" in str(exc)


class TestModeConstants:
    """Tests for mode constants."""

    def test_mode_values(self):
        """Mode constants have expected values."""
        assert MODE_STRICT == "strict"
        assert MODE_PERMISSIVE == "permissive"
        assert MODE_DEBUG == "debug"
        assert MODE_AUDIT == "audit"


class TestSecureAgentRun:
    """Tests for SecureAgent.run()."""

    def test_run_unknown_framework_raises(self):
        """run() raises for unknown frameworks."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        with pytest.raises(UnsupportedFrameworkError):
            secure.run()

    def test_get_pre_action_authorizer_no_policy(self):
        """get_pre_action_authorizer returns None without policy."""
        mock_agent = object()
        secure = SecureAgent(agent=mock_agent)
        authorizer = secure.get_pre_action_authorizer()
        assert authorizer is None


class TestSecureAgentBrowserUseMock:
    """Tests for browser-use framework detection with mocks."""

    def test_detect_browser_use_by_attributes(self):
        """browser-use Agent detected by task/llm/browser attributes."""

        class MockBrowserUseAgent:
            __module__ = "some.module"

            def __init__(self):
                self.task = "Test task"
                self.llm = object()
                self.browser = object()

        MockBrowserUseAgent.__name__ = "Agent"

        result = FrameworkDetector.detect(MockBrowserUseAgent())
        assert result.framework == Framework.BROWSER_USE
        assert result.confidence == 0.8
        assert result.metadata.get("detection") == "duck_typing"

    def test_secure_agent_detects_browser_use(self):
        """SecureAgent correctly detects browser-use agent."""

        class MockBrowserUseAgent:
            __module__ = "browser_use.agent"

            def __init__(self):
                self.task = "Test task"
                self.llm = "mock_llm"

        agent = MockBrowserUseAgent()
        secure = SecureAgent(agent=agent)

        assert secure.framework == Framework.BROWSER_USE
        assert secure.wrapped.executor == "mock_llm"


class TestSecureAgentLangChainMock:
    """Tests for LangChain framework detection with mocks."""

    def test_detect_langchain_by_module(self):
        """LangChain detected by module."""

        class MockAgentExecutor:
            __module__ = "langchain.agents"

        result = FrameworkDetector.detect(MockAgentExecutor())
        assert result.framework == Framework.LANGCHAIN
        assert result.confidence == 1.0

    def test_secure_agent_detects_langchain(self):
        """SecureAgent correctly detects LangChain agent."""

        class MockAgentExecutor:
            __module__ = "langchain.agents.executor"

            def __init__(self):
                self.llm = "mock_llm"

            def invoke(self, inputs):
                return {"output": "result"}

        agent = MockAgentExecutor()
        secure = SecureAgent(agent=agent)

        assert secure.framework == Framework.LANGCHAIN
        assert secure.wrapped.executor == "mock_llm"


class TestSecureAgentPlaywrightMock:
    """Tests for Playwright framework detection with mocks."""

    def test_detect_playwright_by_module(self):
        """Playwright detected by module."""

        class MockPage:
            __module__ = "playwright.async_api._generated"

        result = FrameworkDetector.detect(MockPage())
        assert result.framework == Framework.PLAYWRIGHT
        assert result.confidence == 1.0
        assert result.metadata.get("is_async") is True

    def test_secure_agent_detects_playwright(self):
        """SecureAgent correctly detects Playwright page."""

        class MockPage:
            __module__ = "playwright.sync_api._generated"

        page = MockPage()
        secure = SecureAgent(agent=page)

        assert secure.framework == Framework.PLAYWRIGHT
        assert secure.wrapped.metadata.get("is_async") is False
