"""Configuration classes for predicate-secure."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Mode type alias
Mode = Literal["strict", "permissive", "debug", "audit"]


@dataclass(frozen=True)
class SecureAgentConfig:
    """
    Configuration for SecureAgent.

    Attributes:
        policy: Path to policy file or inline policy dict
        mode: Execution mode (strict, permissive, debug, audit)
        principal_id: Agent principal ID (auto-detect from env if not provided)
        tenant_id: Tenant ID for multi-tenant deployments
        session_id: Session ID for tracking
        sidecar_url: Sidecar URL (None for embedded mode)
        signing_key: Secret key for mandate signing (auto-detect from env if not provided)
        mandate_ttl_seconds: TTL for issued mandates
        fail_closed: Whether to fail closed on authorization errors (based on mode)
    """

    policy: str | Path | None = None
    mode: Mode = "strict"
    principal_id: str | None = None
    tenant_id: str | None = None
    session_id: str | None = None
    sidecar_url: str | None = None
    signing_key: str | None = None
    mandate_ttl_seconds: int = 300

    @property
    def fail_closed(self) -> bool:
        """Whether to fail closed on authorization errors."""
        return self.mode == "strict"

    @property
    def effective_principal_id(self) -> str:
        """Get principal ID, falling back to environment variable."""
        return self.principal_id or os.getenv("PREDICATE_PRINCIPAL_ID", "agent:default")

    @property
    def effective_signing_key(self) -> str:
        """Get signing key, falling back to environment variable."""
        key = self.signing_key or os.getenv("PREDICATE_AUTHORITY_SIGNING_KEY")
        if not key:
            # For embedded mode without sidecar, generate a local key
            # This is fine for local-only operation; production should use env var
            key = "local-dev-key-not-for-production"
        return key

    @property
    def effective_policy_path(self) -> str | None:
        """Get policy path as string."""
        if self.policy is None:
            return os.getenv("PREDICATE_AUTHORITY_POLICY_FILE")
        if isinstance(self.policy, Path):
            return str(self.policy)
        return self.policy

    @classmethod
    def from_kwargs(
        cls,
        policy: str | Path | None = None,
        mode: str = "strict",
        principal_id: str | None = None,
        tenant_id: str | None = None,
        session_id: str | None = None,
        sidecar_url: str | None = None,
        signing_key: str | None = None,
        mandate_ttl_seconds: int = 300,
    ) -> SecureAgentConfig:
        """Create config from keyword arguments with validation."""
        valid_modes = ("strict", "permissive", "debug", "audit")
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {valid_modes}")

        return cls(
            policy=policy,
            mode=mode,  # type: ignore[arg-type]
            principal_id=principal_id,
            tenant_id=tenant_id,
            session_id=session_id,
            sidecar_url=sidecar_url,
            signing_key=signing_key,
            mandate_ttl_seconds=mandate_ttl_seconds,
        )


@dataclass
class WrappedAgent:
    """
    Container for a wrapped agent with its detected framework.

    Attributes:
        original: The original agent object
        framework: Detected framework name
        agent_runtime: Initialized AgentRuntime (if applicable)
        executor: LLM executor extracted from agent (if applicable)
    """

    original: object
    framework: str
    agent_runtime: object | None = None
    executor: object | None = None
    metadata: dict = field(default_factory=dict)
