"""Framework detection for SecureAgent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Framework(Enum):
    """Supported agent frameworks."""

    BROWSER_USE = "browser_use"
    PLAYWRIGHT = "playwright"
    LANGCHAIN = "langchain"
    PYDANTIC_AI = "pydantic_ai"
    OPENCLAW = "openclaw"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectionResult:
    """Result of framework detection."""

    framework: Framework
    agent_type: str
    confidence: float  # 0.0 to 1.0
    metadata: dict


class FrameworkDetector:
    """Detects the framework of a given agent object."""

    @classmethod
    def detect(cls, agent: Any) -> DetectionResult:
        """
        Detect the framework of an agent.

        Args:
            agent: The agent object to detect

        Returns:
            DetectionResult with framework info
        """
        # Check browser-use
        result = cls._check_browser_use(agent)
        if result:
            return result

        # Check Playwright
        result = cls._check_playwright(agent)
        if result:
            return result

        # Check LangChain
        result = cls._check_langchain(agent)
        if result:
            return result

        # Check PydanticAI
        result = cls._check_pydantic_ai(agent)
        if result:
            return result

        # Check OpenClaw
        result = cls._check_openclaw(agent)
        if result:
            return result

        # Unknown framework
        return DetectionResult(
            framework=Framework.UNKNOWN,
            agent_type=type(agent).__name__,
            confidence=0.0,
            metadata={"module": getattr(type(agent), "__module__", "unknown")},
        )

    @classmethod
    def _check_browser_use(cls, agent: Any) -> DetectionResult | None:
        """Check if agent is a browser-use Agent."""
        agent_type = type(agent)
        module = getattr(agent_type, "__module__", "")

        # Check by module path
        if "browser_use" in module:
            return DetectionResult(
                framework=Framework.BROWSER_USE,
                agent_type=agent_type.__name__,
                confidence=1.0,
                metadata={
                    "module": module,
                    "has_task": hasattr(agent, "task"),
                    "has_llm": hasattr(agent, "llm"),
                },
            )

        # Check by class name and attributes (duck typing)
        if agent_type.__name__ == "Agent" and hasattr(agent, "task") and hasattr(agent, "llm"):
            # Could be browser-use, check for more specific attributes
            if hasattr(agent, "browser") or hasattr(agent, "controller"):
                return DetectionResult(
                    framework=Framework.BROWSER_USE,
                    agent_type=agent_type.__name__,
                    confidence=0.8,
                    metadata={"module": module, "detection": "duck_typing"},
                )

        return None

    @classmethod
    def _check_playwright(cls, agent: Any) -> DetectionResult | None:
        """Check if agent is a Playwright Page."""
        agent_type = type(agent)
        module = getattr(agent_type, "__module__", "")

        # Check by module path
        if "playwright" in module:
            # Determine if sync or async
            is_async = "async_api" in module
            return DetectionResult(
                framework=Framework.PLAYWRIGHT,
                agent_type=agent_type.__name__,
                confidence=1.0,
                metadata={
                    "module": module,
                    "is_async": is_async,
                    "is_page": agent_type.__name__ == "Page",
                },
            )

        # Check by duck typing for Page-like objects
        if hasattr(agent, "goto") and hasattr(agent, "click") and hasattr(agent, "evaluate"):
            return DetectionResult(
                framework=Framework.PLAYWRIGHT,
                agent_type=agent_type.__name__,
                confidence=0.7,
                metadata={"module": module, "detection": "duck_typing"},
            )

        return None

    @classmethod
    def _check_langchain(cls, agent: Any) -> DetectionResult | None:
        """Check if agent is a LangChain agent."""
        agent_type = type(agent)
        module = getattr(agent_type, "__module__", "")

        # Check by module path
        if "langchain" in module:
            is_executor = "AgentExecutor" in agent_type.__name__
            return DetectionResult(
                framework=Framework.LANGCHAIN,
                agent_type=agent_type.__name__,
                confidence=1.0,
                metadata={
                    "module": module,
                    "is_executor": is_executor,
                    "has_invoke": hasattr(agent, "invoke"),
                },
            )

        # Check by duck typing
        if hasattr(agent, "invoke") and hasattr(agent, "agent"):
            return DetectionResult(
                framework=Framework.LANGCHAIN,
                agent_type=agent_type.__name__,
                confidence=0.6,
                metadata={"module": module, "detection": "duck_typing"},
            )

        return None

    @classmethod
    def _check_pydantic_ai(cls, agent: Any) -> DetectionResult | None:
        """Check if agent is a PydanticAI agent."""
        agent_type = type(agent)
        module = getattr(agent_type, "__module__", "")

        # Check by module path
        if "pydantic_ai" in module:
            return DetectionResult(
                framework=Framework.PYDANTIC_AI,
                agent_type=agent_type.__name__,
                confidence=1.0,
                metadata={"module": module},
            )

        return None

    @classmethod
    def _check_openclaw(cls, agent: Any) -> DetectionResult | None:
        """Check if agent is an OpenClaw agent wrapper."""
        agent_type = type(agent)
        module = getattr(agent_type, "__module__", "")

        # Check by module path
        if "openclaw" in module.lower():
            return DetectionResult(
                framework=Framework.OPENCLAW,
                agent_type=agent_type.__name__,
                confidence=1.0,
                metadata={"module": module},
            )

        # Check for OpenClaw-specific attributes
        # OpenClaw wrapper would have: process handle, config, skill_url
        if hasattr(agent, "openclaw_process") or hasattr(agent, "openclaw_config"):
            return DetectionResult(
                framework=Framework.OPENCLAW,
                agent_type=agent_type.__name__,
                confidence=0.9,
                metadata={
                    "module": module,
                    "detection": "attribute_based",
                    "has_process": hasattr(agent, "openclaw_process"),
                    "has_config": hasattr(agent, "openclaw_config"),
                },
            )

        # Check if it's a dict-like config for OpenClaw CLI
        if isinstance(agent, dict):
            if "openclaw_cli_path" in agent or "skill_proxy_url" in agent:
                return DetectionResult(
                    framework=Framework.OPENCLAW,
                    agent_type="OpenClawConfig",
                    confidence=0.8,
                    metadata={"detection": "config_dict"},
                )

        return None


class UnsupportedFrameworkError(Exception):
    """Raised when an unsupported framework is detected."""

    def __init__(self, detection: DetectionResult):
        self.detection = detection
        super().__init__(
            f"Unsupported framework: {detection.agent_type} "
            f"(module: {detection.metadata.get('module', 'unknown')}). "
            f"Supported frameworks: browser-use, Playwright, LangChain, PydanticAI"
        )
