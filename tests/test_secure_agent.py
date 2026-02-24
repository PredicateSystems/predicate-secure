"""Tests for SecureAgent."""

import pytest

from predicate_secure import (
    MODE_AUDIT,
    MODE_DEBUG,
    MODE_PERMISSIVE,
    MODE_STRICT,
    AuthorizationDenied,
    PolicyLoadError,
    SecureAgent,
    VerificationFailed,
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


class TestExceptions:
    """Tests for custom exceptions."""

    def test_authorization_denied(self):
        """AuthorizationDenied is an Exception."""
        with pytest.raises(AuthorizationDenied):
            raise AuthorizationDenied("Action denied by policy")

    def test_verification_failed(self):
        """VerificationFailed is an Exception."""
        with pytest.raises(VerificationFailed):
            raise VerificationFailed("Post-execution check failed")

    def test_policy_load_error(self):
        """PolicyLoadError is an Exception."""
        with pytest.raises(PolicyLoadError):
            raise PolicyLoadError("Invalid policy file")


class TestModeConstants:
    """Tests for mode constants."""

    def test_mode_values(self):
        """Mode constants have expected values."""
        assert MODE_STRICT == "strict"
        assert MODE_PERMISSIVE == "permissive"
        assert MODE_DEBUG == "debug"
        assert MODE_AUDIT == "audit"
