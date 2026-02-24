"""
predicate-secure: Drop-in security wrapper for AI agents.

Adds authorization, verification, and audit to any agent framework
(browser-use, LangChain, Playwright, etc.) in 3 lines of code.

Example:
    from predicate_secure import SecureAgent
    from browser_use import Agent

    # Wrap your existing agent
    secure_agent = SecureAgent(
        agent=Agent(task="Buy headphones", llm=my_model),
        policy="policies/shopping.yaml",
        mode="strict",
    )

    # Run with full authorization + verification loop
    secure_agent.run()
"""

from __future__ import annotations

__version__ = "0.1.0"

# Public API - will be implemented in subsequent phases
__all__ = [
    "SecureAgent",
    "SecureAgentConfig",
    "PolicyLoader",
    # Modes
    "MODE_STRICT",
    "MODE_PERMISSIVE",
    "MODE_DEBUG",
    "MODE_AUDIT",
    # Exceptions
    "AuthorizationDenied",
    "VerificationFailed",
    "PolicyLoadError",
]

# Mode constants
MODE_STRICT = "strict"
MODE_PERMISSIVE = "permissive"
MODE_DEBUG = "debug"
MODE_AUDIT = "audit"


class AuthorizationDenied(Exception):
    """Raised when an action is denied by the policy engine."""

    pass


class VerificationFailed(Exception):
    """Raised when post-execution verification fails."""

    pass


class PolicyLoadError(Exception):
    """Raised when a policy file cannot be loaded."""

    pass


# Placeholder classes - to be implemented
class SecureAgentConfig:
    """Configuration for SecureAgent."""

    pass


class PolicyLoader:
    """Loads and validates policy files."""

    pass


class SecureAgent:
    """
    Drop-in security wrapper for AI agents.

    Wraps any agent framework (browser-use, LangChain, Playwright, etc.)
    and adds:
    - Pre-action authorization via policy engine
    - Post-execution verification via snapshot engine
    - Cryptographic audit receipts

    Example:
        secure_agent = SecureAgent(
            agent=my_browser_use_agent,
            policy="policies/shopping.yaml",
            mode="strict",
        )
        secure_agent.run()
    """

    def __init__(
        self,
        agent,
        policy: str | dict | None = None,
        mode: str = MODE_STRICT,
        principal_id: str | None = None,
        sidecar_url: str | None = None,
    ):
        """
        Initialize SecureAgent wrapper.

        Args:
            agent: The agent to wrap (browser-use Agent, Playwright page, etc.)
            policy: Policy file path, dict, or None for default
            mode: Execution mode (strict, permissive, debug, audit)
            principal_id: Agent principal ID (auto-detect from env if not provided)
            sidecar_url: Sidecar URL (None for embedded mode)
        """
        self._agent = agent
        self._policy = policy
        self._mode = mode
        self._principal_id = principal_id
        self._sidecar_url = sidecar_url
        # TODO: Wire up AgentRuntime, AuthorityClient, RuntimeAgent

    def run(self, task: str | None = None):
        """
        Execute the agent with full authorization + verification loop.

        Args:
            task: Optional task override

        Returns:
            Agent execution result
        """
        # TODO: Implement the full loop
        raise NotImplementedError("SecureAgent.run() not yet implemented")

    @classmethod
    def attach(cls, agent, **kwargs) -> "SecureAgent":
        """
        Attach SecureAgent to an existing agent (factory method).

        This mirrors the SentienceDebugger.attach() pattern.

        Args:
            agent: The agent to wrap
            **kwargs: Additional configuration

        Returns:
            SecureAgent instance
        """
        return cls(agent=agent, **kwargs)
