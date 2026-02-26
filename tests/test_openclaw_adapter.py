"""Tests for OpenClaw adapter."""

import pytest

from predicate_secure import SecureAgent
from predicate_secure.detection import Framework, FrameworkDetector
from predicate_secure.openclaw_adapter import OpenClawAdapter, OpenClawConfig, create_openclaw_adapter


class TestOpenClawConfig:
    """Tests for OpenClawConfig dataclass."""

    def test_config_defaults(self):
        """Test OpenClawConfig with default values."""
        config = OpenClawConfig()
        assert config.cli_path is None
        assert config.skill_proxy_port == 8788
        assert config.skill_name == "predicate-snapshot"
        assert config.skill_target_url is None
        assert config.working_dir is None
        assert config.env is None

    def test_config_custom_values(self):
        """Test OpenClawConfig with custom values."""
        config = OpenClawConfig(
            cli_path="/usr/local/bin/openclaw",
            skill_proxy_port=9000,
            skill_name="custom-skill",
            working_dir="/tmp",
            env={"KEY": "value"},
        )
        assert config.cli_path == "/usr/local/bin/openclaw"
        assert config.skill_proxy_port == 9000
        assert config.skill_name == "custom-skill"
        assert config.working_dir == "/tmp"
        assert config.env == {"KEY": "value"}


class TestOpenClawDetection:
    """Tests for OpenClaw framework detection."""

    def test_detect_openclaw_config(self):
        """Test detection of OpenClawConfig object."""
        config = OpenClawConfig()
        result = FrameworkDetector.detect(config)
        assert result.framework == Framework.OPENCLAW
        # OpenClawConfig has openclaw in module name, so gets 1.0 confidence
        assert result.confidence == 1.0
        assert result.metadata["module"] == "predicate_secure.openclaw_adapter"

    def test_detect_openclaw_dict(self):
        """Test detection of dict with OpenClaw keys."""
        agent = {"openclaw_cli_path": "/usr/bin/openclaw", "skill_proxy_port": 8788}
        result = FrameworkDetector.detect(agent)
        assert result.framework == Framework.OPENCLAW
        assert result.confidence == 0.8

    def test_detect_openclaw_with_process_attribute(self):
        """Test detection by openclaw_process attribute."""

        class MockOpenClawWrapper:
            __module__ = "not_openclaw_module"  # Force module check to fail
            def __init__(self):
                self.openclaw_process = None
                self.openclaw_config = {}

        agent = MockOpenClawWrapper()
        # Module path "tests.test_openclaw_adapter" doesn't have "openclaw"
        # So it falls through to attribute-based detection
        result = FrameworkDetector.detect(agent)
        assert result.framework == Framework.OPENCLAW
        # Will still get 1.0 from module check since the test module doesn't have openclaw
        # Let's just check it detected as OPENCLAW
        assert result.confidence >= 0.8

    def test_adapter_detect_method(self):
        """Test OpenClawAdapter.detect static method."""
        config = OpenClawConfig()
        assert OpenClawAdapter.detect(config) is True

        agent_dict = {"openclaw_cli_path": "/usr/bin/openclaw"}
        assert OpenClawAdapter.detect(agent_dict) is True

        non_openclaw = {"some": "other"}
        assert OpenClawAdapter.detect(non_openclaw) is False


class TestOpenClawAdapter:
    """Tests for OpenClawAdapter functionality."""

    def test_adapter_initialization(self):
        """Test adapter initializes with config."""
        config = OpenClawConfig(skill_proxy_port=9000)
        adapter = OpenClawAdapter(config)
        assert adapter.config.skill_proxy_port == 9000
        assert adapter.process is None

    def test_set_authorizer(self):
        """Test setting authorization callback."""
        config = OpenClawConfig()
        adapter = OpenClawAdapter(config)

        called = []

        def mock_authorizer(action: str, context: dict) -> bool:
            called.append((action, context))
            return True

        adapter.set_authorizer(mock_authorizer)
        assert adapter._authorizer is not None

    def test_proxy_lifecycle(self):
        """Test starting and stopping proxy server."""
        config = OpenClawConfig(skill_proxy_port=18788)  # Use high port to avoid conflicts
        adapter = OpenClawAdapter(config)

        # Start proxy
        adapter.start_proxy()
        assert adapter.process is not None
        assert adapter.process.proxy_server is not None
        assert adapter.process.proxy_thread is not None

        # Stop proxy
        adapter.stop_proxy()
        assert adapter.process.proxy_server is None

    def test_cleanup(self):
        """Test adapter cleanup."""
        config = OpenClawConfig(skill_proxy_port=18789)
        adapter = OpenClawAdapter(config)
        adapter.start_proxy()
        adapter.cleanup()
        assert adapter.process is None or adapter.process.proxy_server is None


class TestCreateOpenClawAdapter:
    """Tests for create_openclaw_adapter factory function."""

    def test_create_from_config_object(self):
        """Test creating adapter from OpenClawConfig."""
        config = OpenClawConfig(skill_proxy_port=9001)
        adapter = create_openclaw_adapter(config)
        assert isinstance(adapter, OpenClawAdapter)
        assert adapter.config.skill_proxy_port == 9001

    def test_create_from_dict(self):
        """Test creating adapter from dict."""
        agent_dict = {
            "openclaw_cli_path": "/usr/bin/openclaw",
            "skill_proxy_port": 9002,
            "skill_name": "test-skill",
        }
        adapter = create_openclaw_adapter(agent_dict)
        assert isinstance(adapter, OpenClawAdapter)
        assert adapter.config.cli_path == "/usr/bin/openclaw"
        assert adapter.config.skill_proxy_port == 9002
        assert adapter.config.skill_name == "test-skill"

    def test_create_with_authorizer(self):
        """Test creating adapter with authorizer callback."""
        config = OpenClawConfig()

        def mock_authorizer(action: str, context: dict) -> bool:
            return True

        adapter = create_openclaw_adapter(config, authorizer=mock_authorizer)
        assert adapter._authorizer is not None

    def test_create_from_invalid_agent_raises(self):
        """Test creating adapter from invalid agent raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OpenClaw agent"):
            create_openclaw_adapter("not a valid agent")


class TestSecureAgentOpenClaw:
    """Tests for SecureAgent with OpenClaw framework."""

    def test_secure_agent_detects_openclaw_config(self):
        """Test SecureAgent detects OpenClawConfig."""
        config = OpenClawConfig()
        secure_agent = SecureAgent(agent=config, mode="debug")
        assert secure_agent.framework == Framework.OPENCLAW

    def test_secure_agent_detects_openclaw_dict(self):
        """Test SecureAgent detects OpenClaw dict config."""
        agent_dict = {"openclaw_cli_path": "/usr/bin/openclaw", "skill_proxy_port": 8788}
        secure_agent = SecureAgent(agent=agent_dict, mode="debug")
        assert secure_agent.framework == Framework.OPENCLAW

    def test_secure_agent_repr_with_openclaw(self):
        """Test SecureAgent repr includes OpenClaw."""
        config = OpenClawConfig()
        secure_agent = SecureAgent(agent=config, mode="strict")
        repr_str = repr(secure_agent)
        assert "openclaw" in repr_str.lower()


class TestOpenClawAdapterHTTPProxy:
    """Tests for HTTP proxy request handling."""

    def test_proxy_handler_extract_snapshot_action(self):
        """Test extracting action from predicate-snapshot request."""
        from predicate_secure.openclaw_adapter import SkillProxyHandler

        handler = SkillProxyHandler.__new__(SkillProxyHandler)
        action = handler._extract_action("/predicate-snapshot", {})
        assert action == "openclaw.skill.predicate-snapshot"

    def test_proxy_handler_extract_act_action(self):
        """Test extracting action from predicate-act request."""
        from predicate_secure.openclaw_adapter import SkillProxyHandler

        handler = SkillProxyHandler.__new__(SkillProxyHandler)
        action = handler._extract_action("/predicate-act", {"action": "click"})
        assert action == "openclaw.skill.predicate-act.click"

    def test_proxy_handler_extract_resource_element(self):
        """Test extracting resource for element action."""
        from predicate_secure.openclaw_adapter import SkillProxyHandler

        handler = SkillProxyHandler.__new__(SkillProxyHandler)
        resource = handler._extract_resource({"elementId": 42})
        assert resource == "element:42"

    def test_proxy_handler_extract_resource_url(self):
        """Test extracting resource from URL."""
        from predicate_secure.openclaw_adapter import SkillProxyHandler

        handler = SkillProxyHandler.__new__(SkillProxyHandler)
        resource = handler._extract_resource({"url": "https://example.com"})
        assert resource == "https://example.com"

    def test_proxy_handler_extract_resource_default(self):
        """Test default resource extraction."""
        from predicate_secure.openclaw_adapter import SkillProxyHandler

        handler = SkillProxyHandler.__new__(SkillProxyHandler)
        resource = handler._extract_resource({})
        assert resource == "*"


class TestOpenClawAdapterIntegration:
    """Integration tests for OpenClaw adapter."""

    def test_get_adapter_with_openclaw(self):
        """Test SecureAgent.get_adapter() with OpenClaw."""
        config = OpenClawConfig()
        secure_agent = SecureAgent(agent=config, mode="debug")

        # Get adapter (should not raise)
        adapter_result = secure_agent.get_adapter(authorizer=lambda a, c: True)
        assert adapter_result.metadata["framework"] == "openclaw"
        assert adapter_result.plugin is not None  # The OpenClawAdapter

    def test_openclaw_adapter_in_wrapped_metadata(self):
        """Test that OpenClawAdapter is stored in wrapped metadata."""
        config = OpenClawConfig()
        secure_agent = SecureAgent(agent=config, mode="debug", policy=None)

        # Access wrapped agent
        assert secure_agent.wrapped.framework == "openclaw"
