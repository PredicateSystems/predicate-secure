"""Framework adapters for predicate-secure.

This module wires together existing adapters from sdk-python
to provide seamless integration with various agent frameworks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .detection import Framework

if TYPE_CHECKING:
    pass


@dataclass
class AdapterResult:
    """Result of adapter initialization."""

    agent_runtime: Any | None
    backend: Any | None
    tracer: Any | None
    plugin: Any | None
    executor: Any | None
    metadata: dict


class AdapterError(Exception):
    """Raised when adapter initialization fails."""

    def __init__(self, message: str, framework: Framework):
        super().__init__(message)
        self.framework = framework


def create_browser_use_adapter(
    agent: Any,
    tracer: Any | None = None,
    snapshot_options: Any | None = None,
    predicate_api_key: str | None = None,
) -> AdapterResult:
    """
    Create adapter for browser-use Agent.

    This wires together:
    - BrowserUseAdapter for CDP backend
    - PredicateBrowserUsePlugin for lifecycle hooks
    - AgentRuntime from the session

    Args:
        agent: browser-use Agent instance
        tracer: Optional Tracer for event emission
        snapshot_options: Optional SnapshotOptions
        predicate_api_key: Optional API key for Predicate API

    Returns:
        AdapterResult with initialized components

    Raises:
        AdapterError: If browser-use or predicate packages not available
    """
    try:
        from predicate.backends.browser_use_adapter import BrowserUseAdapter
        from predicate.integrations.browser_use.plugin import (
            PredicateBrowserUsePlugin,
            PredicateBrowserUsePluginConfig,
        )
    except ImportError as e:
        raise AdapterError(
            "browser-use adapter requires predicate[browser-use]. "
            f"Install with: pip install predicate-secure[browser-use]. Error: {e}",
            Framework.BROWSER_USE,
        ) from e

    # Extract session from agent
    session = getattr(agent, "browser", None) or getattr(agent, "session", None)
    if session is None:
        raise AdapterError(
            "Could not find browser session on agent. "
            "Ensure agent has .browser or .session attribute.",
            Framework.BROWSER_USE,
        )

    # Create adapter
    adapter = BrowserUseAdapter(session)

    # Create plugin config
    plugin_config = PredicateBrowserUsePluginConfig(
        predicate_api_key=predicate_api_key,
        tracer=tracer,
        snapshot_options=snapshot_options,
    )
    plugin = PredicateBrowserUsePlugin(config=plugin_config)

    # Extract executor (LLM)
    executor = getattr(agent, "llm", None)

    return AdapterResult(
        agent_runtime=None,  # Created lazily by plugin
        backend=adapter,
        tracer=tracer,
        plugin=plugin,
        executor=executor,
        metadata={
            "framework": "browser_use",
            "has_session": session is not None,
            "has_executor": executor is not None,
        },
    )


async def create_browser_use_runtime(
    agent: Any,
    tracer: Any | None = None,
    snapshot_options: Any | None = None,
    predicate_api_key: str | None = None,
) -> AdapterResult:
    """
    Create AgentRuntime for browser-use Agent (async).

    This creates a full AgentRuntime that can be used with RuntimeAgent.

    Args:
        agent: browser-use Agent instance
        tracer: Optional Tracer for event emission
        snapshot_options: Optional SnapshotOptions
        predicate_api_key: Optional API key for Predicate API

    Returns:
        AdapterResult with initialized AgentRuntime
    """
    try:
        from predicate.agent_runtime import AgentRuntime
        from predicate.backends.browser_use_adapter import BrowserUseAdapter
        from predicate.tracing import JsonlTraceSink
        from predicate.tracing import Tracer as PredicateTracer
    except ImportError as e:
        raise AdapterError(
            f"browser-use adapter requires predicate. Error: {e}",
            Framework.BROWSER_USE,
        ) from e

    # Extract session from agent
    session = getattr(agent, "browser", None) or getattr(agent, "session", None)
    if session is None:
        raise AdapterError(
            "Could not find browser session on agent.",
            Framework.BROWSER_USE,
        )

    # Create adapter and backend
    adapter = BrowserUseAdapter(session)
    backend = await adapter.create_backend()

    # Create tracer if not provided
    if tracer is None:
        import uuid

        run_id = f"secure-{uuid.uuid4().hex[:8]}"
        sink = JsonlTraceSink(f"trace-{run_id}.jsonl")
        tracer = PredicateTracer(run_id=run_id, sink=sink)

    # Create runtime
    runtime = AgentRuntime(
        backend=backend,
        tracer=tracer,
        snapshot_options=snapshot_options,
        predicate_api_key=predicate_api_key,
    )

    return AdapterResult(
        agent_runtime=runtime,
        backend=backend,
        tracer=tracer,
        plugin=None,
        executor=getattr(agent, "llm", None),
        metadata={"framework": "browser_use", "has_runtime": True},
    )


def create_playwright_adapter(
    page: Any,
    tracer: Any | None = None,
    snapshot_options: Any | None = None,
    predicate_api_key: str | None = None,
) -> AdapterResult:
    """
    Create adapter for Playwright Page.

    Uses AgentRuntime.from_playwright_page() factory.

    Args:
        page: Playwright Page instance (sync or async)
        tracer: Optional Tracer for event emission
        snapshot_options: Optional SnapshotOptions
        predicate_api_key: Optional API key for Predicate API

    Returns:
        AdapterResult with initialized AgentRuntime
    """
    try:
        from predicate.agent_runtime import AgentRuntime
        from predicate.tracing import JsonlTraceSink
        from predicate.tracing import Tracer as PredicateTracer
    except ImportError as e:
        raise AdapterError(
            f"Playwright adapter requires predicate. Error: {e}",
            Framework.PLAYWRIGHT,
        ) from e

    # Create tracer if not provided
    if tracer is None:
        import uuid

        run_id = f"secure-{uuid.uuid4().hex[:8]}"
        sink = JsonlTraceSink(f"trace-{run_id}.jsonl")
        tracer = PredicateTracer(run_id=run_id, sink=sink)

    # Create runtime from Playwright page
    runtime = AgentRuntime.from_playwright_page(
        page=page,
        tracer=tracer,
        snapshot_options=snapshot_options,
        predicate_api_key=predicate_api_key,
    )

    return AdapterResult(
        agent_runtime=runtime,
        backend=runtime.backend,
        tracer=tracer,
        plugin=None,
        executor=None,
        metadata={"framework": "playwright", "has_runtime": True},
    )


def create_langchain_adapter(
    agent: Any,
    browser: Any | None = None,
    tracer: Any | None = None,
    snapshot_options: Any | None = None,
    predicate_api_key: str | None = None,
) -> AdapterResult:
    """
    Create adapter for LangChain agent.

    Uses SentienceLangChainCore for tool interception.

    Args:
        agent: LangChain AgentExecutor or similar
        browser: Optional browser instance for browser tools
        tracer: Optional Tracer for event emission
        snapshot_options: Optional SnapshotOptions (currently unused)
        predicate_api_key: Optional API key for Predicate API (currently unused)

    Returns:
        AdapterResult with initialized components
    """
    try:
        from predicate.integrations.langchain.context import SentienceLangChainContext
        from predicate.integrations.langchain.core import SentienceLangChainCore
    except ImportError as e:
        raise AdapterError(
            f"LangChain adapter requires predicate[langchain]. Error: {e}",
            Framework.LANGCHAIN,
        ) from e

    # LangChain context requires a browser instance
    # If not provided, we can still create the adapter but core won't work fully
    if browser is None:
        # Return adapter without core - just for detection/metadata
        executor = getattr(agent, "llm", None) or getattr(agent, "agent", None)
        return AdapterResult(
            agent_runtime=None,
            backend=None,
            tracer=tracer,
            plugin=None,  # No core without browser
            executor=executor,
            metadata={
                "framework": "langchain",
                "has_browser": False,
                "agent_type": type(agent).__name__,
                "note": "Provide browser parameter to enable SentienceLangChainCore",
            },
        )

    # Create context with browser
    ctx = SentienceLangChainContext(
        browser=browser,
        tracer=tracer,
    )

    # Create core wrapper
    core = SentienceLangChainCore(ctx)

    # Extract executor/LLM
    executor = getattr(agent, "llm", None) or getattr(agent, "agent", None)

    return AdapterResult(
        agent_runtime=None,  # LangChain uses different pattern
        backend=None,
        tracer=tracer,
        plugin=core,  # Core acts as plugin for tool interception
        executor=executor,
        metadata={
            "framework": "langchain",
            "has_browser": True,
            "agent_type": type(agent).__name__,
        },
    )


def create_pydantic_ai_adapter(
    agent: Any,
    tracer: Any | None = None,
) -> AdapterResult:
    """
    Create adapter for PydanticAI agent.

    Args:
        agent: PydanticAI Agent instance
        tracer: Optional Tracer for event emission

    Returns:
        AdapterResult with initialized components
    """
    # PydanticAI integration is simpler - extract model
    executor = getattr(agent, "model", None)

    return AdapterResult(
        agent_runtime=None,
        backend=None,
        tracer=tracer,
        plugin=None,
        executor=executor,
        metadata={
            "framework": "pydantic_ai",
            "model": str(executor) if executor else None,
        },
    )


def create_openclaw_adapter(
    agent: Any,
    authorizer: Any | None = None,
) -> AdapterResult:
    """
    Create adapter for OpenClaw CLI agent.

    Args:
        agent: OpenClaw config dict or OpenClawConfig object
        authorizer: Optional authorization callback

    Returns:
        AdapterResult with OpenClawAdapter

    Raises:
        AdapterError: If OpenClaw adapter initialization fails
    """
    try:
        from .openclaw_adapter import OpenClawAdapter, OpenClawConfig, create_openclaw_adapter as create_adapter_impl
    except ImportError as e:
        raise AdapterError(
            f"OpenClaw adapter requires openclaw_adapter module. Error: {e}",
            Framework.OPENCLAW,
        ) from e

    try:
        adapter = create_adapter_impl(agent, authorizer)
        return AdapterResult(
            agent_runtime=None,  # OpenClaw uses HTTP proxy pattern
            backend=None,
            tracer=None,
            plugin=adapter,  # The adapter itself acts as the plugin
            executor=None,
            metadata={
                "framework": "openclaw",
                "proxy_port": adapter.config.skill_proxy_port,
                "skill_name": adapter.config.skill_name,
            },
        )
    except Exception as e:
        raise AdapterError(
            f"Failed to create OpenClaw adapter: {e}",
            Framework.OPENCLAW,
        ) from e


def create_adapter(
    agent: Any,
    framework: Framework,
    tracer: Any | None = None,
    snapshot_options: Any | None = None,
    predicate_api_key: str | None = None,
    **kwargs: Any,
) -> AdapterResult:
    """
    Create adapter for the given framework.

    This is the main entry point for adapter creation.

    Args:
        agent: The agent or page to wrap
        framework: Detected framework
        tracer: Optional Tracer for event emission
        snapshot_options: Optional SnapshotOptions
        predicate_api_key: Optional API key
        **kwargs: Additional framework-specific options

    Returns:
        AdapterResult with initialized components

    Raises:
        AdapterError: If framework is not supported
    """
    if framework == Framework.BROWSER_USE:
        return create_browser_use_adapter(agent, tracer, snapshot_options, predicate_api_key)

    if framework == Framework.PLAYWRIGHT:
        return create_playwright_adapter(agent, tracer, snapshot_options, predicate_api_key)

    if framework == Framework.LANGCHAIN:
        browser = kwargs.get("browser")
        return create_langchain_adapter(agent, browser, tracer, snapshot_options, predicate_api_key)

    if framework == Framework.PYDANTIC_AI:
        return create_pydantic_ai_adapter(agent, tracer)

    if framework == Framework.OPENCLAW:
        authorizer = kwargs.get("authorizer")
        return create_openclaw_adapter(agent, authorizer)

    raise AdapterError(
        f"No adapter available for framework: {framework.value}",
        framework,
    )
