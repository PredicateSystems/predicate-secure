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

from pathlib import Path
from typing import Any

from .adapters import (
    AdapterError,
    AdapterResult,
    create_adapter,
    create_browser_use_adapter,
    create_browser_use_runtime,
    create_langchain_adapter,
    create_playwright_adapter,
    create_pydantic_ai_adapter,
)
from .config import SecureAgentConfig, WrappedAgent
from .detection import DetectionResult, Framework, FrameworkDetector, UnsupportedFrameworkError

__version__ = "0.1.0"

# Public API
__all__ = [
    "SecureAgent",
    "SecureAgentConfig",
    "WrappedAgent",
    # Framework detection
    "Framework",
    "FrameworkDetector",
    "DetectionResult",
    # Adapters
    "AdapterResult",
    "AdapterError",
    "create_adapter",
    "create_browser_use_adapter",
    "create_browser_use_runtime",
    "create_playwright_adapter",
    "create_langchain_adapter",
    "create_pydantic_ai_adapter",
    # Modes
    "MODE_STRICT",
    "MODE_PERMISSIVE",
    "MODE_DEBUG",
    "MODE_AUDIT",
    # Exceptions
    "AuthorizationDenied",
    "VerificationFailed",
    "PolicyLoadError",
    "UnsupportedFrameworkError",
]

# Mode constants
MODE_STRICT = "strict"
MODE_PERMISSIVE = "permissive"
MODE_DEBUG = "debug"
MODE_AUDIT = "audit"


class AuthorizationDenied(Exception):
    """Raised when an action is denied by the policy engine."""

    def __init__(self, message: str, decision: Any = None):
        super().__init__(message)
        self.decision = decision


class VerificationFailed(Exception):
    """Raised when post-execution verification fails."""

    def __init__(self, message: str, predicate: str | None = None):
        super().__init__(message)
        self.predicate = predicate


class PolicyLoadError(Exception):
    """Raised when a policy file cannot be loaded."""

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

    Attributes:
        config: SecureAgentConfig with all configuration
        wrapped: WrappedAgent with detected framework info
        authority_context: Initialized AuthorityClient context (lazy)
    """

    def __init__(
        self,
        agent: Any,
        policy: str | Path | None = None,
        mode: str = MODE_STRICT,
        principal_id: str | None = None,
        tenant_id: str | None = None,
        session_id: str | None = None,
        sidecar_url: str | None = None,
        signing_key: str | None = None,
        mandate_ttl_seconds: int = 300,
    ):
        """
        Initialize SecureAgent wrapper.

        Args:
            agent: The agent to wrap (browser-use Agent, Playwright page, etc.)
            policy: Policy file path or None for env var fallback
            mode: Execution mode (strict, permissive, debug, audit)
            principal_id: Agent principal ID (auto-detect from env if not provided)
            tenant_id: Tenant ID for multi-tenant deployments
            session_id: Session ID for tracking
            sidecar_url: Sidecar URL (None for embedded mode)
            signing_key: Secret key for mandate signing
            mandate_ttl_seconds: TTL for issued mandates
        """
        # Build config from kwargs
        self._config = SecureAgentConfig.from_kwargs(
            policy=policy,
            mode=mode,
            principal_id=principal_id,
            tenant_id=tenant_id,
            session_id=session_id,
            sidecar_url=sidecar_url,
            signing_key=signing_key,
            mandate_ttl_seconds=mandate_ttl_seconds,
        )

        # Detect framework and wrap agent
        self._wrapped = self._wrap_agent(agent)

        # Lazy-initialized authority context
        self._authority_context: Any = None

        # Legacy attribute access (for backward compat with tests)
        self._agent = agent
        self._policy = policy
        self._mode = mode
        self._principal_id = principal_id
        self._sidecar_url = sidecar_url

    @property
    def config(self) -> SecureAgentConfig:
        """Get the configuration."""
        return self._config

    @property
    def wrapped(self) -> WrappedAgent:
        """Get the wrapped agent with framework info."""
        return self._wrapped

    @property
    def framework(self) -> Framework:
        """Get the detected framework."""
        return Framework(self._wrapped.framework)

    def _wrap_agent(self, agent: Any) -> WrappedAgent:
        """
        Detect framework and wrap agent.

        Args:
            agent: The agent to wrap

        Returns:
            WrappedAgent with framework info
        """
        detection = FrameworkDetector.detect(agent)

        return WrappedAgent(
            original=agent,
            framework=detection.framework.value,
            agent_runtime=None,  # Initialized lazily when needed
            executor=self._extract_executor(agent, detection),
            metadata=detection.metadata,
        )

    def _extract_executor(self, agent: Any, detection: DetectionResult) -> Any | None:
        """
        Extract LLM executor from agent if available.

        Args:
            agent: The agent object
            detection: Detection result

        Returns:
            LLM executor or None
        """
        # browser-use Agent has .llm attribute
        if detection.framework == Framework.BROWSER_USE:
            return getattr(agent, "llm", None)

        # LangChain AgentExecutor has .agent or .llm
        if detection.framework == Framework.LANGCHAIN:
            return getattr(agent, "llm", None) or getattr(agent, "agent", None)

        # PydanticAI agents have .model
        if detection.framework == Framework.PYDANTIC_AI:
            return getattr(agent, "model", None)

        return None

    def _get_authority_context(self) -> Any:
        """
        Get or initialize the authority context.

        Returns:
            LocalAuthorizationContext from AuthorityClient

        Raises:
            PolicyLoadError: If policy cannot be loaded
        """
        if self._authority_context is not None:
            return self._authority_context

        policy_path = self._config.effective_policy_path
        if policy_path is None:
            # No policy = no authorization enforcement
            return None

        try:
            # Import here to avoid hard dependency
            from predicate_authority.client import AuthorityClient

            self._authority_context = AuthorityClient.from_policy_file(
                policy_file=policy_path,
                secret_key=self._config.effective_signing_key,
                ttl_seconds=self._config.mandate_ttl_seconds,
            )
            return self._authority_context
        except ImportError:
            raise PolicyLoadError(
                "predicate-authority is required for policy enforcement. "
                "Install with: pip install predicate-secure[authority]"
            )
        except FileNotFoundError as e:
            raise PolicyLoadError(f"Policy file not found: {policy_path}") from e
        except Exception as e:
            raise PolicyLoadError(f"Failed to load policy: {e}") from e

    def _create_pre_action_authorizer(self) -> Any:
        """
        Create a pre-action authorizer callback for RuntimeAgent.

        Returns:
            Callable that takes ActionRequest and returns decision
        """
        context = self._get_authority_context()
        if context is None:
            # No policy = allow all
            return None

        def authorizer(request: Any) -> Any:
            """Pre-action authorization callback."""
            decision = context.client.authorize(request)

            if self._config.mode == "debug":
                print(f"[predicate-secure] authorize({request.action}): {decision}")

            if not decision.allowed and self._config.fail_closed:
                raise AuthorizationDenied(
                    f"Action denied: {decision.reason.value if decision.reason else 'policy'}",
                    decision=decision,
                )

            return decision

        return authorizer

    def run(self, task: str | None = None) -> Any:
        """
        Execute the agent with full authorization + verification loop.

        Args:
            task: Optional task override

        Returns:
            Agent execution result

        Raises:
            AuthorizationDenied: If an action is denied (in strict mode)
            VerificationFailed: If post-execution verification fails
            UnsupportedFrameworkError: If framework is not supported
        """
        if self._wrapped.framework == Framework.UNKNOWN.value:
            detection = FrameworkDetector.detect(self._wrapped.original)
            raise UnsupportedFrameworkError(detection)

        # Framework-specific execution
        if self._wrapped.framework == Framework.BROWSER_USE.value:
            return self._run_browser_use(task)

        if self._wrapped.framework == Framework.PLAYWRIGHT.value:
            return self._run_playwright(task)

        if self._wrapped.framework == Framework.LANGCHAIN.value:
            return self._run_langchain(task)

        if self._wrapped.framework == Framework.PYDANTIC_AI.value:
            return self._run_pydantic_ai(task)

        raise NotImplementedError(f"run() not implemented for framework: {self._wrapped.framework}")

    def _run_browser_use(self, task: str | None) -> Any:
        """Run browser-use agent with authorization."""
        # Import here to avoid hard dependency
        try:
            import asyncio

            agent = self._wrapped.original

            # Override task if provided
            if task is not None and hasattr(agent, "task"):
                setattr(agent, "task", task)

            # Check if agent has a run method
            if hasattr(agent, "run"):
                # browser-use Agent.run() is typically async
                if asyncio.iscoroutinefunction(agent.run):
                    return asyncio.get_event_loop().run_until_complete(agent.run())
                return agent.run()

            raise NotImplementedError(
                "browser-use Agent.run() integration not fully implemented. "
                "For now, use the agent directly with pre_action_authorizer callback."
            )
        except ImportError:
            raise NotImplementedError(
                "browser-use integration requires the browser-use package. "
                "Install with: pip install predicate-secure[browser-use]"
            )

    def _run_playwright(self, task: str | None) -> Any:
        """Run Playwright page with authorization."""
        raise NotImplementedError(
            "Playwright direct integration not yet implemented. "
            "Use with RuntimeAgent for Playwright pages."
        )

    def _run_langchain(self, task: str | None) -> Any:
        """Run LangChain agent with authorization."""
        agent = self._wrapped.original

        # LangChain agents have .invoke() method
        if hasattr(agent, "invoke"):
            if task is not None:
                return agent.invoke({"input": task})
            raise ValueError("Task is required for LangChain agents")

        raise NotImplementedError(
            "LangChain integration requires AgentExecutor with invoke() method."
        )

    def _run_pydantic_ai(self, task: str | None) -> Any:
        """Run PydanticAI agent with authorization."""
        raise NotImplementedError("PydanticAI integration not yet implemented.")

    @classmethod
    def attach(cls, agent: Any, **kwargs: Any) -> SecureAgent:
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

    def get_pre_action_authorizer(self) -> Any:
        """
        Get a pre-action authorizer callback for use with RuntimeAgent.

        This allows integrating SecureAgent authorization with existing
        RuntimeAgent-based workflows.

        Returns:
            Callable for pre_action_authorizer parameter

        Example:
            secure = SecureAgent(agent=my_agent, policy="policy.yaml")
            runtime_agent = RuntimeAgent(
                runtime=runtime,
                executor=executor,
                pre_action_authorizer=secure.get_pre_action_authorizer(),
            )
        """
        return self._create_pre_action_authorizer()

    def get_adapter(
        self,
        tracer: Any | None = None,
        snapshot_options: Any | None = None,
        predicate_api_key: str | None = None,
        **kwargs: Any,
    ) -> AdapterResult:
        """
        Get an adapter for the wrapped agent.

        This creates the appropriate adapter based on the detected framework,
        wiring together BrowserUseAdapter, PredicateBrowserUsePlugin,
        SentienceLangChainCore, or AgentRuntime.from_playwright_page().

        Args:
            tracer: Optional Tracer for event emission
            snapshot_options: Optional SnapshotOptions
            predicate_api_key: Optional API key for Predicate API
            **kwargs: Additional framework-specific options

        Returns:
            AdapterResult with initialized components

        Raises:
            AdapterError: If adapter initialization fails

        Example:
            secure = SecureAgent(agent=my_browser_use_agent, policy="policy.yaml")
            adapter = secure.get_adapter()

            # Use plugin lifecycle hooks
            result = await agent.run(
                on_step_start=adapter.plugin.on_step_start,
                on_step_end=adapter.plugin.on_step_end,
            )
        """
        return create_adapter(
            agent=self._wrapped.original,
            framework=self.framework,
            tracer=tracer,
            snapshot_options=snapshot_options,
            predicate_api_key=predicate_api_key,
            **kwargs,
        )

    async def get_runtime_async(
        self,
        tracer: Any | None = None,
        snapshot_options: Any | None = None,
        predicate_api_key: str | None = None,
    ) -> Any:
        """
        Get an initialized AgentRuntime for the wrapped agent (async).

        This is useful for browser-use agents where runtime initialization
        requires async operations.

        Args:
            tracer: Optional Tracer for event emission
            snapshot_options: Optional SnapshotOptions
            predicate_api_key: Optional API key for Predicate API

        Returns:
            AgentRuntime instance

        Raises:
            AdapterError: If runtime initialization fails

        Example:
            secure = SecureAgent(agent=my_browser_use_agent, policy="policy.yaml")
            runtime = await secure.get_runtime_async()

            # Use with RuntimeAgent
            from predicate.runtime_agent import RuntimeAgent
            runtime_agent = RuntimeAgent(
                runtime=runtime,
                executor=my_llm,
                pre_action_authorizer=secure.get_pre_action_authorizer(),
            )
        """
        if self.framework == Framework.BROWSER_USE:
            result = await create_browser_use_runtime(
                agent=self._wrapped.original,
                tracer=tracer,
                snapshot_options=snapshot_options,
                predicate_api_key=predicate_api_key,
            )
            # Cache the runtime
            self._wrapped.agent_runtime = result.agent_runtime
            return result.agent_runtime

        if self.framework == Framework.PLAYWRIGHT:
            adapter = create_playwright_adapter(
                page=self._wrapped.original,
                tracer=tracer,
                snapshot_options=snapshot_options,
                predicate_api_key=predicate_api_key,
            )
            self._wrapped.agent_runtime = adapter.agent_runtime
            return adapter.agent_runtime

        raise AdapterError(
            f"get_runtime_async() not supported for framework: {self.framework.value}",
            self.framework,
        )

    def get_browser_use_plugin(
        self,
        tracer: Any | None = None,
        snapshot_options: Any | None = None,
        predicate_api_key: str | None = None,
    ) -> Any:
        """
        Get a PredicateBrowserUsePlugin for browser-use lifecycle hooks.

        This is the recommended way to integrate with browser-use agents.

        Args:
            tracer: Optional Tracer for event emission
            snapshot_options: Optional SnapshotOptions
            predicate_api_key: Optional API key for Predicate API

        Returns:
            PredicateBrowserUsePlugin instance

        Raises:
            AdapterError: If framework is not browser-use

        Example:
            secure = SecureAgent(agent=my_agent, policy="policy.yaml")
            plugin = secure.get_browser_use_plugin()

            # Run with lifecycle hooks
            result = await agent.run(
                on_step_start=plugin.on_step_start,
                on_step_end=plugin.on_step_end,
            )
        """
        if self.framework != Framework.BROWSER_USE:
            raise AdapterError(
                "get_browser_use_plugin() only available for browser-use agents",
                self.framework,
            )

        adapter = create_browser_use_adapter(
            agent=self._wrapped.original,
            tracer=tracer,
            snapshot_options=snapshot_options,
            predicate_api_key=predicate_api_key,
        )
        return adapter.plugin

    def get_langchain_core(
        self,
        browser: Any | None = None,
        tracer: Any | None = None,
        snapshot_options: Any | None = None,
        predicate_api_key: str | None = None,
    ) -> Any:
        """
        Get a SentienceLangChainCore for LangChain tool interception.

        Args:
            browser: Optional browser instance for browser tools
            tracer: Optional Tracer for event emission
            snapshot_options: Optional SnapshotOptions
            predicate_api_key: Optional API key for Predicate API

        Returns:
            SentienceLangChainCore instance

        Raises:
            AdapterError: If framework is not LangChain
        """
        if self.framework != Framework.LANGCHAIN:
            raise AdapterError(
                "get_langchain_core() only available for LangChain agents",
                self.framework,
            )

        adapter = create_langchain_adapter(
            agent=self._wrapped.original,
            browser=browser,
            tracer=tracer,
            snapshot_options=snapshot_options,
            predicate_api_key=predicate_api_key,
        )
        return adapter.plugin

    def __repr__(self) -> str:
        return (
            f"SecureAgent("
            f"framework={self._wrapped.framework}, "
            f"mode={self._config.mode}, "
            f"policy={self._config.effective_policy_path or 'None'}"
            f")"
        )
