"""Debug tracing for predicate-secure.

This module provides human-readable and machine-parseable trace output
for debugging agent executions with authorization and verification.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import IO, Any, Literal


class TraceFormat(str, Enum):
    """Output format for trace events."""

    CONSOLE = "console"
    JSON = "json"


@dataclass
class TraceEvent:
    """A single trace event in the execution flow."""

    event_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict = field(default_factory=dict)
    step_number: int | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }
        if self.step_number is not None:
            result["step_number"] = self.step_number
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class SnapshotDiff:
    """Represents a diff between two snapshots."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[dict] = field(default_factory=list)  # {"element": str, "before": str, "after": str}

    def is_empty(self) -> bool:
        """Check if diff is empty (no changes)."""
        return not (self.added or self.removed or self.changed)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PolicyDecision:
    """Represents a policy decision with explanation."""

    action: str
    resource: str
    allowed: bool
    reason: str | None = None
    policy_rule: str | None = None
    principal: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class VerificationResult:
    """Represents a verification predicate result."""

    predicate: str
    passed: bool
    message: str | None = None
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class DebugTracer:
    """
    Tracer for debug mode output.

    Outputs human-readable trace information to console or file,
    with optional JSON format for machine parsing.

    Example:
        tracer = DebugTracer(format="console")
        tracer.trace_step_start(1, "click", "button#submit")
        tracer.trace_policy_decision(decision)
        tracer.trace_step_end(1, duration_ms=150)
    """

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
    }

    def __init__(
        self,
        format: Literal["console", "json"] = "console",
        output: IO[str] | None = None,
        file_path: str | Path | None = None,
        use_colors: bool = True,
        verbose: bool = True,
    ):
        """
        Initialize the debug tracer.

        Args:
            format: Output format ("console" or "json")
            output: Output stream (defaults to sys.stderr for console, file for json)
            file_path: Path to trace file (for json format or file output)
            use_colors: Whether to use ANSI colors (console format only)
            verbose: Whether to output verbose information
        """
        self.format = TraceFormat(format)
        self.use_colors = use_colors and self.format == TraceFormat.CONSOLE
        self.verbose = verbose
        self._step_count = 0
        self._start_time: float | None = None
        self._step_start_times: dict[int, float] = {}
        self._events: list[TraceEvent] = []

        # Set up output stream
        self._file_handle: IO[str] | None = None
        self.output: IO[str]
        if file_path:
            self._file_handle = open(file_path, "a")
            self.output = self._file_handle
        elif output:
            self.output = output
        else:
            self.output = sys.stderr

    def close(self) -> None:
        """Close the file handle if opened."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self) -> DebugTracer:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _emit(self, event: TraceEvent) -> None:
        """Emit a trace event."""
        self._events.append(event)

        if self.format == TraceFormat.JSON:
            self.output.write(event.to_json() + "\n")
            self.output.flush()
        # Console format is handled by specific trace methods

    def trace_session_start(
        self,
        framework: str,
        mode: str,
        policy: str | None = None,
        principal_id: str | None = None,
    ) -> None:
        """Trace session start."""
        self._start_time = time.time()
        self._step_count = 0

        event = TraceEvent(
            event_type="session_start",
            data={
                "framework": framework,
                "mode": mode,
                "policy": policy,
                "principal_id": principal_id,
            },
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            self.output.write("\n")
            self.output.write(self._color("=" * 60, "bold") + "\n")
            self.output.write(
                self._color("[predicate-secure]", "cyan")
                + " Session Start\n"
            )
            self.output.write(f"  Framework: {self._color(framework, 'blue')}\n")
            self.output.write(f"  Mode: {self._color(mode, 'yellow')}\n")
            if policy:
                self.output.write(f"  Policy: {policy}\n")
            if principal_id:
                self.output.write(f"  Principal: {principal_id}\n")
            self.output.write(self._color("=" * 60, "bold") + "\n\n")
            self.output.flush()

    def trace_session_end(self, success: bool = True, error: str | None = None) -> None:
        """Trace session end."""
        duration_ms = None
        if self._start_time:
            duration_ms = (time.time() - self._start_time) * 1000

        event = TraceEvent(
            event_type="session_end",
            data={
                "success": success,
                "error": error,
                "total_steps": self._step_count,
            },
            duration_ms=duration_ms,
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            self.output.write("\n")
            self.output.write(self._color("=" * 60, "bold") + "\n")
            status = (
                self._color("SUCCESS", "green")
                if success
                else self._color("FAILED", "red")
            )
            self.output.write(
                self._color("[predicate-secure]", "cyan")
                + f" Session End: {status}\n"
            )
            self.output.write(f"  Total Steps: {self._step_count}\n")
            if duration_ms:
                self.output.write(f"  Duration: {duration_ms:.1f}ms\n")
            if error:
                self.output.write(f"  Error: {self._color(error, 'red')}\n")
            self.output.write(self._color("=" * 60, "bold") + "\n")
            self.output.flush()

    def trace_step_start(
        self,
        step_number: int | None = None,
        action: str = "",
        resource: str = "",
        metadata: dict | None = None,
    ) -> int:
        """
        Trace step start.

        Args:
            step_number: Step number (auto-incremented if None)
            action: Action being performed
            resource: Resource being acted upon
            metadata: Additional metadata

        Returns:
            The step number
        """
        if step_number is None:
            self._step_count += 1
            step_number = self._step_count
        else:
            self._step_count = max(self._step_count, step_number)

        self._step_start_times[step_number] = time.time()

        event = TraceEvent(
            event_type="step_start",
            step_number=step_number,
            data={
                "action": action,
                "resource": resource,
                **(metadata or {}),
            },
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            self.output.write(
                self._color(f"[Step {step_number}]", "bold")
                + f" {self._color(action, 'magenta')}"
            )
            if resource:
                self.output.write(f" → {self._color(resource, 'blue')}")
            self.output.write("\n")
            self.output.flush()

        return step_number

    def trace_step_end(
        self,
        step_number: int,
        success: bool = True,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Trace step end."""
        duration_ms = None
        if step_number in self._step_start_times:
            duration_ms = (time.time() - self._step_start_times[step_number]) * 1000
            del self._step_start_times[step_number]

        event = TraceEvent(
            event_type="step_end",
            step_number=step_number,
            duration_ms=duration_ms,
            data={
                "success": success,
                "result": str(result) if result else None,
                "error": error,
            },
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE and self.verbose:
            status = (
                self._color("OK", "green")
                if success
                else self._color("FAILED", "red")
            )
            duration_str = f" ({duration_ms:.1f}ms)" if duration_ms else ""
            self.output.write(f"  └─ {status}{duration_str}\n")
            if error:
                self.output.write(f"     Error: {self._color(error, 'red')}\n")
            self.output.write("\n")
            self.output.flush()

    def trace_policy_decision(
        self,
        decision: PolicyDecision | dict,
    ) -> None:
        """Trace a policy decision."""
        if isinstance(decision, dict):
            decision = PolicyDecision(**decision)

        event = TraceEvent(
            event_type="policy_decision",
            data=decision.to_dict(),
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            status = (
                self._color("ALLOWED", "green")
                if decision.allowed
                else self._color("DENIED", "red")
            )
            self.output.write(f"  ├─ Policy: {status}\n")
            self.output.write(f"  │  Action: {decision.action}\n")
            self.output.write(f"  │  Resource: {decision.resource}\n")
            if decision.reason:
                self.output.write(f"  │  Reason: {decision.reason}\n")
            if decision.policy_rule:
                self.output.write(
                    f"  │  Rule: {self._color(decision.policy_rule, 'dim')}\n"
                )
            self.output.flush()

    def trace_snapshot_diff(
        self,
        diff: SnapshotDiff | dict,
        label: str = "State Change",
    ) -> None:
        """Trace snapshot diff (before/after state change)."""
        if isinstance(diff, dict):
            diff = SnapshotDiff(**diff)

        event = TraceEvent(
            event_type="snapshot_diff",
            data={
                "label": label,
                **diff.to_dict(),
            },
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            if diff.is_empty():
                self.output.write(
                    f"  ├─ {label}: {self._color('(no changes)', 'dim')}\n"
                )
            else:
                self.output.write(f"  ├─ {label}:\n")
                for added in diff.added:
                    self.output.write(
                        f"  │  {self._color('+', 'green')} {added}\n"
                    )
                for removed in diff.removed:
                    self.output.write(
                        f"  │  {self._color('-', 'red')} {removed}\n"
                    )
                for changed in diff.changed:
                    self.output.write(
                        f"  │  {self._color('~', 'yellow')} {changed.get('element', 'unknown')}\n"
                    )
                    if self.verbose:
                        before = changed.get("before", "")
                        after = changed.get("after", "")
                        if before:
                            self.output.write(
                                f"  │    Before: {self._color(str(before)[:50], 'dim')}\n"
                            )
                        if after:
                            self.output.write(
                                f"  │    After:  {self._color(str(after)[:50], 'dim')}\n"
                            )
            self.output.flush()

    def trace_verification_result(
        self,
        result: VerificationResult | dict,
    ) -> None:
        """Trace verification predicate result."""
        if isinstance(result, dict):
            result = VerificationResult(**result)

        event = TraceEvent(
            event_type="verification_result",
            data=result.to_dict(),
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            status = (
                self._color("PASS", "green")
                if result.passed
                else self._color("FAIL", "red")
            )
            self.output.write(f"  ├─ Verification: {status}\n")
            self.output.write(f"  │  Predicate: {result.predicate}\n")
            if result.message:
                self.output.write(f"  │  Message: {result.message}\n")
            if not result.passed and self.verbose:
                if result.expected is not None:
                    self.output.write(f"  │  Expected: {result.expected}\n")
                if result.actual is not None:
                    self.output.write(f"  │  Actual: {result.actual}\n")
            self.output.flush()

    def trace_authorization_request(
        self,
        action: str,
        resource: str,
        principal: str | None = None,
        context: dict | None = None,
    ) -> None:
        """Trace an authorization request."""
        event = TraceEvent(
            event_type="authorization_request",
            data={
                "action": action,
                "resource": resource,
                "principal": principal,
                "context": context,
            },
        )
        self._emit(event)

        if self.format == TraceFormat.CONSOLE:
            self.output.write(f"  ├─ Authorize: {action} on {resource}\n")
            if principal:
                self.output.write(f"  │  Principal: {principal}\n")
            self.output.flush()

    def trace_custom(self, event_type: str, data: dict) -> None:
        """Trace a custom event."""
        event = TraceEvent(event_type=event_type, data=data)
        self._emit(event)

        if self.format == TraceFormat.CONSOLE and self.verbose:
            self.output.write(f"  ├─ {event_type}: {json.dumps(data)}\n")
            self.output.flush()

    def get_events(self) -> list[TraceEvent]:
        """Get all recorded trace events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear recorded events."""
        self._events.clear()


def create_debug_tracer(
    format: Literal["console", "json"] = "console",
    file_path: str | Path | None = None,
    use_colors: bool = True,
    verbose: bool = True,
) -> DebugTracer:
    """
    Factory function to create a debug tracer.

    Args:
        format: Output format ("console" or "json")
        file_path: Path to trace file (optional)
        use_colors: Whether to use ANSI colors
        verbose: Whether to output verbose information

    Returns:
        Configured DebugTracer instance
    """
    return DebugTracer(
        format=format,
        file_path=file_path,
        use_colors=use_colors,
        verbose=verbose,
    )
