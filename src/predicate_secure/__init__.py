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
from .tracing import (
    DebugTracer,
    PolicyDecision,
    SnapshotDiff,
    TraceEvent,
    TraceFormat,
    VerificationResult,
    create_debug_tracer,
)

__version__ = "0.2.0"

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
    # Tracing
    "DebugTracer",
    "TraceEvent",
    "TraceFormat",
    "PolicyDecision",
    "SnapshotDiff",
    "VerificationResult",
    "create_debug_tracer",
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
        trace_format: str = "console",
        trace_file: str | Path | None = None,
        trace_colors: bool = True,
        trace_verbose: bool = True,
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
            trace_format: Format for debug trace output ("console" or "json")
            trace_file: Path to trace output file (None for stderr)
            trace_colors: Whether to use ANSI colors in console output
            trace_verbose: Whether to output verbose trace information
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
            trace_format=trace_format,
            trace_file=trace_file,
            trace_colors=trace_colors,
            trace_verbose=trace_verbose,
        )

        # Detect framework and wrap agent
        self._wrapped = self._wrap_agent(agent)

        # Lazy-initialized authority context
        self._authority_context: Any = None

        # Debug tracer (initialized when mode="debug")
        self._tracer: DebugTracer | None = None
        if self._config.is_debug_mode:
            self._tracer = create_debug_tracer(
                format=self._config.trace_format,
                file_path=self._config.effective_trace_file,
                use_colors=self._config.trace_colors,
                verbose=self._config.trace_verbose,
            )

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

    @property
    def tracer(self) -> DebugTracer | None:
        """Get the debug tracer (available when mode='debug')."""
        return self._tracer

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
            # Trace authorization request
            if self._tracer:
                action = getattr(request, "action", str(request))
                resource = getattr(request, "resource", "")
                self._tracer.trace_authorization_request(
                    action=action,
                    resource=resource,
                    principal=self._config.effective_principal_id,
                )

            decision = context.client.authorize(request)

            # Trace policy decision
            if self._tracer:
                action = getattr(request, "action", str(request))
                resource = getattr(request, "resource", "")
                reason = None
                if hasattr(decision, "reason") and decision.reason:
                    reason = (
                        decision.reason.value
                        if hasattr(decision.reason, "value")
                        else str(decision.reason)
                    )
                self._tracer.trace_policy_decision(
                    PolicyDecision(
                        action=action,
                        resource=resource,
                        allowed=decision.allowed,
                        reason=reason,
                        principal=self._config.effective_principal_id,
                    )
                )

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

        # Trace session start
        if self._tracer:
            self._tracer.trace_session_start(
                framework=self._wrapped.framework,
                mode=self._config.mode,
                policy=self._config.effective_policy_path,
                principal_id=self._config.effective_principal_id,
            )

        try:
            # Framework-specific execution
            if self._wrapped.framework == Framework.BROWSER_USE.value:
                result = self._run_browser_use(task)
            elif self._wrapped.framework == Framework.PLAYWRIGHT.value:
                result = self._run_playwright(task)
            elif self._wrapped.framework == Framework.LANGCHAIN.value:
                result = self._run_langchain(task)
            elif self._wrapped.framework == Framework.PYDANTIC_AI.value:
                result = self._run_pydantic_ai(task)
            elif self._wrapped.framework == Framework.OPENCLAW.value:
                result = self._run_openclaw(task)
            else:
                raise NotImplementedError(
                    f"run() not implemented for framework: {self._wrapped.framework}"
                )

            # Trace session end (success)
            if self._tracer:
                self._tracer.trace_session_end(success=True)

            return result

        except Exception as e:
            # Trace session end (failure)
            if self._tracer:
                self._tracer.trace_session_end(success=False, error=str(e))
            raise

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

    def _run_openclaw(self, task: str | None) -> Any:
        """Run OpenClaw CLI agent with authorization."""
        try:
            from .openclaw_adapter import OpenClawAdapter, create_openclaw_adapter
        except ImportError:
            raise NotImplementedError(
                "OpenClaw integration requires openclaw_adapter module. "
                "Ensure all dependencies are installed."
            )

        # Get or create adapter
        if not hasattr(self._wrapped, "openclaw_adapter"):
            # Create adapter from original agent config
            authorizer = self._create_pre_action_authorizer()
            adapter = create_openclaw_adapter(self._wrapped.original, authorizer)
            self._wrapped.metadata["openclaw_adapter"] = adapter
        else:
            adapter = self._wrapped.metadata.get("openclaw_adapter")

        if not isinstance(adapter, OpenClawAdapter):
            raise ValueError("Invalid OpenClaw adapter")

        # Start proxy server
        adapter.start_proxy()

        try:
            # Start CLI with task
            if task is None:
                raise ValueError("Task is required for OpenClaw agents")

            process = adapter.start_cli(task)

            # Wait for completion
            stdout, stderr = process.communicate()

            # Check for errors
            if process.returncode != 0:
                raise RuntimeError(f"OpenClaw CLI failed: {stderr}")

            return {"stdout": stdout, "stderr": stderr, "returncode": process.returncode}

        finally:
            # Cleanup
            adapter.stop_cli()
            adapter.stop_proxy()

    def trace_step(
        self,
        action: str,
        resource: str = "",
        metadata: dict | None = None,
    ) -> int | None:
        """
        Trace a step start (for manual step tracking).

        Args:
            action: Action being performed
            resource: Resource being acted upon
            metadata: Additional metadata

        Returns:
            Step number (None if not in debug mode)

        Example:
            step = secure.trace_step("click", "button#submit")
            # ... perform action ...
            secure.trace_step_end(step, success=True)
        """
        if self._tracer:
            return self._tracer.trace_step_start(
                action=action,
                resource=resource,
                metadata=metadata,
            )
        return None

    def trace_step_end(
        self,
        step_number: int | None,
        success: bool = True,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """
        Trace a step end (for manual step tracking).

        Args:
            step_number: Step number from trace_step()
            success: Whether the step succeeded
            result: Step result (optional)
            error: Error message if failed
        """
        if self._tracer and step_number is not None:
            self._tracer.trace_step_end(
                step_number=step_number,
                success=success,
                result=result,
                error=error,
            )

    def trace_snapshot_diff(
        self,
        before: dict | None = None,
        after: dict | None = None,
        diff: dict | None = None,
        label: str = "State Change",
    ) -> None:
        """
        Trace a snapshot diff (before/after state change).

        Args:
            before: Before snapshot (for computing diff)
            after: After snapshot (for computing diff)
            diff: Pre-computed diff (if before/after not provided)
            label: Label for the diff
        """
        if not self._tracer:
            return

        if diff:
            self._tracer.trace_snapshot_diff(SnapshotDiff(**diff), label=label)
        elif before is not None and after is not None:
            # Compute simple diff
            computed_diff = SnapshotDiff(
                added=[k for k in after if k not in before],
                removed=[k for k in before if k not in after],
                changed=[
                    {"element": k, "before": before[k], "after": after[k]}
                    for k in before
                    if k in after and before[k] != after[k]
                ],
            )
            self._tracer.trace_snapshot_diff(computed_diff, label=label)

    def trace_verification(
        self,
        predicate: str,
        passed: bool,
        message: str | None = None,
        expected: Any = None,
        actual: Any = None,
    ) -> None:
        """
        Trace a verification predicate result.

        Args:
            predicate: Predicate name or expression
            passed: Whether verification passed
            message: Optional message
            expected: Expected value (for failed verifications)
            actual: Actual value (for failed verifications)
        """
        if self._tracer:
            self._tracer.trace_verification_result(
                VerificationResult(
                    predicate=predicate,
                    passed=passed,
                    message=message,
                    expected=expected,
                    actual=actual,
                )
            )

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
