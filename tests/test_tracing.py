"""Tests for debug tracing functionality."""

import io
import json
import tempfile
from pathlib import Path

from predicate_secure import (
    DebugTracer,
    PolicyDecision,
    SecureAgent,
    SnapshotDiff,
    TraceEvent,
    TraceFormat,
    VerificationResult,
    create_debug_tracer,
)


class TestTraceEvent:
    """Tests for TraceEvent dataclass."""

    def test_trace_event_to_dict(self):
        """TraceEvent converts to dict correctly."""
        event = TraceEvent(
            event_type="test_event",
            timestamp="2024-01-01T00:00:00Z",
            data={"key": "value"},
            step_number=1,
            duration_ms=100.5,
        )
        d = event.to_dict()

        assert d["event_type"] == "test_event"
        assert d["timestamp"] == "2024-01-01T00:00:00Z"
        assert d["data"] == {"key": "value"}
        assert d["step_number"] == 1
        assert d["duration_ms"] == 100.5

    def test_trace_event_to_dict_optional_fields(self):
        """TraceEvent omits optional fields when None."""
        event = TraceEvent(event_type="minimal")
        d = event.to_dict()

        assert "step_number" not in d
        assert "duration_ms" not in d

    def test_trace_event_to_json(self):
        """TraceEvent converts to valid JSON."""
        event = TraceEvent(event_type="test", data={"foo": "bar"})
        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "test"
        assert parsed["data"]["foo"] == "bar"


class TestSnapshotDiff:
    """Tests for SnapshotDiff dataclass."""

    def test_snapshot_diff_is_empty(self):
        """SnapshotDiff.is_empty() works correctly."""
        empty_diff = SnapshotDiff()
        assert empty_diff.is_empty() is True

        diff_with_added = SnapshotDiff(added=["element1"])
        assert diff_with_added.is_empty() is False

        diff_with_removed = SnapshotDiff(removed=["element1"])
        assert diff_with_removed.is_empty() is False

        diff_with_changed = SnapshotDiff(changed=[{"element": "x", "before": "a", "after": "b"}])
        assert diff_with_changed.is_empty() is False

    def test_snapshot_diff_to_dict(self):
        """SnapshotDiff converts to dict correctly."""
        diff = SnapshotDiff(
            added=["new_element"],
            removed=["old_element"],
            changed=[{"element": "modified", "before": "x", "after": "y"}],
        )
        d = diff.to_dict()

        assert d["added"] == ["new_element"]
        assert d["removed"] == ["old_element"]
        assert len(d["changed"]) == 1


class TestPolicyDecision:
    """Tests for PolicyDecision dataclass."""

    def test_policy_decision_to_dict(self):
        """PolicyDecision converts to dict correctly."""
        decision = PolicyDecision(
            action="click",
            resource="button#submit",
            allowed=True,
            reason="policy_allowed",
            policy_rule="allow_submit_buttons",
            principal="agent:test",
        )
        d = decision.to_dict()

        assert d["action"] == "click"
        assert d["resource"] == "button#submit"
        assert d["allowed"] is True
        assert d["reason"] == "policy_allowed"
        assert d["policy_rule"] == "allow_submit_buttons"
        assert d["principal"] == "agent:test"


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_result_to_dict(self):
        """VerificationResult converts to dict correctly."""
        result = VerificationResult(
            predicate="cart_updated",
            passed=False,
            message="Cart count mismatch",
            expected=1,
            actual=0,
        )
        d = result.to_dict()

        assert d["predicate"] == "cart_updated"
        assert d["passed"] is False
        assert d["message"] == "Cart count mismatch"
        assert d["expected"] == 1
        assert d["actual"] == 0


class TestDebugTracerConsole:
    """Tests for DebugTracer console output."""

    def test_tracer_session_start(self):
        """Tracer outputs session start correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_session_start(
            framework="browser_use",
            mode="debug",
            policy="test.yaml",
            principal_id="agent:test",
        )

        out = output.getvalue()
        assert "Session Start" in out
        assert "browser_use" in out
        assert "debug" in out
        assert "test.yaml" in out
        assert "agent:test" in out

    def test_tracer_session_end(self):
        """Tracer outputs session end correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_session_start(framework="test", mode="debug")
        tracer.trace_session_end(success=True)

        out = output.getvalue()
        assert "Session End" in out
        assert "SUCCESS" in out

    def test_tracer_session_end_failure(self):
        """Tracer outputs failure correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_session_end(success=False, error="Test error")

        out = output.getvalue()
        assert "FAILED" in out
        assert "Test error" in out

    def test_tracer_step_start(self):
        """Tracer outputs step start correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        step = tracer.trace_step_start(action="click", resource="button#submit")

        out = output.getvalue()
        assert "[Step 1]" in out
        assert "click" in out
        assert "button#submit" in out
        assert step == 1

    def test_tracer_step_auto_increment(self):
        """Tracer auto-increments step numbers."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        step1 = tracer.trace_step_start(action="action1")
        step2 = tracer.trace_step_start(action="action2")
        step3 = tracer.trace_step_start(action="action3")

        assert step1 == 1
        assert step2 == 2
        assert step3 == 3

    def test_tracer_step_end(self):
        """Tracer outputs step end correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        step = tracer.trace_step_start(action="click")
        tracer.trace_step_end(step, success=True)

        out = output.getvalue()
        assert "OK" in out

    def test_tracer_step_end_failure(self):
        """Tracer outputs step failure correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        step = tracer.trace_step_start(action="click")
        tracer.trace_step_end(step, success=False, error="Element not found")

        out = output.getvalue()
        assert "FAILED" in out
        assert "Element not found" in out

    def test_tracer_policy_decision_allowed(self):
        """Tracer outputs allowed policy decision correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_policy_decision(
            PolicyDecision(action="click", resource="button", allowed=True)
        )

        out = output.getvalue()
        assert "ALLOWED" in out
        assert "click" in out
        assert "button" in out

    def test_tracer_policy_decision_denied(self):
        """Tracer outputs denied policy decision correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_policy_decision(
            PolicyDecision(
                action="delete",
                resource="database",
                allowed=False,
                reason="policy_denied",
            )
        )

        out = output.getvalue()
        assert "DENIED" in out
        assert "delete" in out
        assert "database" in out
        assert "policy_denied" in out

    def test_tracer_snapshot_diff(self):
        """Tracer outputs snapshot diff correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_snapshot_diff(
            SnapshotDiff(
                added=["new_element"],
                removed=["old_element"],
                changed=[{"element": "modified", "before": "x", "after": "y"}],
            )
        )

        out = output.getvalue()
        assert "+" in out
        assert "new_element" in out
        assert "-" in out
        assert "old_element" in out
        assert "~" in out
        assert "modified" in out

    def test_tracer_snapshot_diff_empty(self):
        """Tracer handles empty diff correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_snapshot_diff(SnapshotDiff())

        out = output.getvalue()
        assert "(no changes)" in out

    def test_tracer_verification_pass(self):
        """Tracer outputs passed verification correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_verification_result(
            VerificationResult(predicate="item_in_cart", passed=True)
        )

        out = output.getvalue()
        assert "PASS" in out
        assert "item_in_cart" in out

    def test_tracer_verification_fail(self):
        """Tracer outputs failed verification correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output, use_colors=False)

        tracer.trace_verification_result(
            VerificationResult(
                predicate="cart_count",
                passed=False,
                message="Count mismatch",
                expected=1,
                actual=0,
            )
        )

        out = output.getvalue()
        assert "FAIL" in out
        assert "cart_count" in out
        assert "Count mismatch" in out
        assert "Expected: 1" in out
        assert "Actual: 0" in out


class TestDebugTracerJson:
    """Tests for DebugTracer JSON output."""

    def test_tracer_json_session_start(self):
        """Tracer outputs JSON session start correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="json", output=output)

        tracer.trace_session_start(framework="test", mode="debug")

        lines = output.getvalue().strip().split("\n")
        event = json.loads(lines[0])

        assert event["event_type"] == "session_start"
        assert event["data"]["framework"] == "test"
        assert event["data"]["mode"] == "debug"

    def test_tracer_json_step(self):
        """Tracer outputs JSON step events correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="json", output=output)

        tracer.trace_step_start(action="click", resource="button")
        tracer.trace_step_end(1, success=True)

        lines = output.getvalue().strip().split("\n")
        start_event = json.loads(lines[0])
        end_event = json.loads(lines[1])

        assert start_event["event_type"] == "step_start"
        assert start_event["step_number"] == 1
        assert end_event["event_type"] == "step_end"
        assert end_event["step_number"] == 1

    def test_tracer_json_policy_decision(self):
        """Tracer outputs JSON policy decision correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="json", output=output)

        tracer.trace_policy_decision(
            PolicyDecision(action="click", resource="button", allowed=True)
        )

        lines = output.getvalue().strip().split("\n")
        event = json.loads(lines[0])

        assert event["event_type"] == "policy_decision"
        assert event["data"]["action"] == "click"
        assert event["data"]["allowed"] is True


class TestDebugTracerFile:
    """Tests for DebugTracer file output."""

    def test_tracer_file_output(self):
        """Tracer writes to file correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            file_path = f.name

        try:
            tracer = DebugTracer(format="json", file_path=file_path)
            tracer.trace_session_start(framework="test", mode="debug")
            tracer.trace_step_start(action="click")
            tracer.close()

            with open(file_path) as f:
                lines = f.readlines()

            assert len(lines) == 2

            event1 = json.loads(lines[0])
            assert event1["event_type"] == "session_start"

            event2 = json.loads(lines[1])
            assert event2["event_type"] == "step_start"

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_tracer_context_manager(self):
        """Tracer works as context manager."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            file_path = f.name

        try:
            with DebugTracer(format="json", file_path=file_path) as tracer:
                tracer.trace_session_start(framework="test", mode="debug")

            with open(file_path) as f:
                lines = f.readlines()

            assert len(lines) == 1

        finally:
            Path(file_path).unlink(missing_ok=True)


class TestDebugTracerEvents:
    """Tests for DebugTracer event collection."""

    def test_tracer_get_events(self):
        """Tracer collects events correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output)

        tracer.trace_session_start(framework="test", mode="debug")
        tracer.trace_step_start(action="click")
        tracer.trace_session_end(success=True)

        events = tracer.get_events()
        assert len(events) == 3
        assert events[0].event_type == "session_start"
        assert events[1].event_type == "step_start"
        assert events[2].event_type == "session_end"

    def test_tracer_clear_events(self):
        """Tracer clears events correctly."""
        output = io.StringIO()
        tracer = DebugTracer(format="console", output=output)

        tracer.trace_session_start(framework="test", mode="debug")
        assert len(tracer.get_events()) == 1

        tracer.clear_events()
        assert len(tracer.get_events()) == 0


class TestCreateDebugTracer:
    """Tests for create_debug_tracer factory function."""

    def test_create_debug_tracer_console(self):
        """create_debug_tracer creates console tracer."""
        tracer = create_debug_tracer(format="console")
        assert tracer.format == TraceFormat.CONSOLE

    def test_create_debug_tracer_json(self):
        """create_debug_tracer creates JSON tracer."""
        tracer = create_debug_tracer(format="json")
        assert tracer.format == TraceFormat.JSON


class TestSecureAgentDebugMode:
    """Tests for SecureAgent debug mode integration."""

    def test_secure_agent_debug_mode_creates_tracer(self):
        """SecureAgent creates tracer in debug mode."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"
            model = "test"

        secure = SecureAgent(agent=MockAgent(), mode="debug")
        assert secure.tracer is not None
        assert isinstance(secure.tracer, DebugTracer)

    def test_secure_agent_non_debug_mode_no_tracer(self):
        """SecureAgent doesn't create tracer in non-debug modes."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"
            model = "test"

        secure_strict = SecureAgent(agent=MockAgent(), mode="strict")
        assert secure_strict.tracer is None

        secure_permissive = SecureAgent(agent=MockAgent(), mode="permissive")
        assert secure_permissive.tracer is None

        secure_audit = SecureAgent(agent=MockAgent(), mode="audit")
        assert secure_audit.tracer is None

    def test_secure_agent_debug_mode_json_format(self):
        """SecureAgent respects trace_format parameter."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"

        secure = SecureAgent(agent=MockAgent(), mode="debug", trace_format="json")
        assert secure.tracer is not None
        assert secure.tracer.format == TraceFormat.JSON

    def test_secure_agent_trace_step(self):
        """SecureAgent.trace_step() works correctly."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"

        secure = SecureAgent(agent=MockAgent(), mode="debug")
        step = secure.trace_step("click", "button#submit")

        assert step == 1

    def test_secure_agent_trace_step_non_debug(self):
        """SecureAgent.trace_step() returns None in non-debug mode."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"

        secure = SecureAgent(agent=MockAgent(), mode="strict")
        step = secure.trace_step("click", "button#submit")

        assert step is None

    def test_secure_agent_trace_snapshot_diff(self):
        """SecureAgent.trace_snapshot_diff() works correctly."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"

        secure = SecureAgent(agent=MockAgent(), mode="debug")

        # Should not raise
        secure.trace_snapshot_diff(
            before={"element1": "value1"},
            after={"element1": "value2", "element2": "new"},
        )

        events = secure.tracer.get_events()
        diff_events = [e for e in events if e.event_type == "snapshot_diff"]
        assert len(diff_events) == 1

    def test_secure_agent_trace_verification(self):
        """SecureAgent.trace_verification() works correctly."""

        class MockAgent:
            __module__ = "pydantic_ai.agent"

        secure = SecureAgent(agent=MockAgent(), mode="debug")

        secure.trace_verification(
            predicate="cart_updated",
            passed=True,
            message="Cart has 1 item",
        )

        events = secure.tracer.get_events()
        verification_events = [e for e in events if e.event_type == "verification_result"]
        assert len(verification_events) == 1
        assert verification_events[0].data["passed"] is True


class TestSecureAgentDebugModeFile:
    """Tests for SecureAgent debug mode with file output."""

    def test_secure_agent_debug_mode_file_output(self):
        """SecureAgent writes trace to file in debug mode."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            file_path = f.name

        try:

            class MockAgent:
                __module__ = "pydantic_ai.agent"
                model = "test"

            secure = SecureAgent(
                agent=MockAgent(),
                mode="debug",
                trace_format="json",
                trace_file=file_path,
            )

            # Write some trace events
            secure.trace_step("click", "button")

            # Close the tracer to flush
            secure.tracer.close()

            # Read the file
            with open(file_path) as f:
                lines = f.readlines()

            assert len(lines) >= 1
            event = json.loads(lines[0])
            assert event["event_type"] == "step_start"

        finally:
            Path(file_path).unlink(missing_ok=True)
