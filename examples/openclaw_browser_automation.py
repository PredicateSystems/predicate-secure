"""
Example: Secure OpenClaw agent with authorization and verification.

This example demonstrates how to wrap an OpenClaw CLI agent with predicate-secure
to add pre-action authorization and audit logging for browser automation tasks.

Prerequisites:
    1. OpenClaw CLI installed (npm install -g openclaw)
    2. predicate-snapshot skill installed in OpenClaw
    3. Policy file (policies/openclaw_browser.yaml)
"""

from pathlib import Path

from predicate_secure import SecureAgent
from predicate_secure.openclaw_adapter import OpenClawConfig

# Example policy file content (create this as policies/openclaw_browser.yaml):
EXAMPLE_POLICY = """
rules:
  # Allow OpenClaw snapshot skill
  - action: "openclaw.skill.predicate-snapshot"
    resource: "*"
    effect: allow

  # Allow clicking on known safe domains
  - action: "openclaw.skill.predicate-act.click"
    resource: "element:*"
    effect: allow
    conditions:
      # Only allow on safe domains (you'd check current URL in real policy)
      - domain_matches: ["*.example.com", "*.trusted-site.com"]

  # Allow typing in form fields (with restrictions)
  - action: "openclaw.skill.predicate-act.type"
    resource: "element:*"
    effect: allow
    conditions:
      # Prevent entering sensitive data
      - not_contains: ["password", "ssn", "credit"]

  # Block scrolling to prevent UI confusion
  - action: "openclaw.skill.predicate-act.scroll"
    resource: "*"
    effect: deny

  # Default deny for safety
  - action: "*"
    resource: "*"
    effect: deny
"""


def main():
    """Run OpenClaw agent with secure authorization."""
    # Create OpenClaw configuration
    openclaw_config = OpenClawConfig(
        cli_path="/usr/local/bin/openclaw",  # Or None to use PATH
        skill_proxy_port=8788,  # Port for HTTP proxy
        skill_name="predicate-snapshot",
        working_dir=str(Path.home() / ".openclaw"),
    )

    # You could also use a dict instead of OpenClawConfig:
    # openclaw_config = {
    #     "openclaw_cli_path": "/usr/local/bin/openclaw",
    #     "skill_proxy_port": 8788,
    #     "skill_name": "predicate-snapshot",
    # }

    # Create policy file
    policy_dir = Path("policies")
    policy_dir.mkdir(exist_ok=True)
    policy_file = policy_dir / "openclaw_browser.yaml"

    if not policy_file.exists():
        policy_file.write_text(EXAMPLE_POLICY)
        print(f"Created example policy at {policy_file}")

    # Wrap OpenClaw with SecureAgent
    secure_agent = SecureAgent(
        agent=openclaw_config,
        policy=str(policy_file),
        mode="strict",  # Fail-closed mode
        principal_id="openclaw-agent-01",
        trace_format="console",
    )

    print(f"[predicate-secure] Detected framework: {secure_agent.framework.value}")
    print(f"[predicate-secure] Mode: {secure_agent.config.mode}")
    print(f"[predicate-secure] Policy: {secure_agent.config.effective_policy_path}")

    # Example task
    task = "Navigate to example.com and take a snapshot"

    print(f"\n[OpenClaw] Running task: {task}")
    print("[predicate-secure] Starting HTTP proxy for skill interception...")

    try:
        # Run the OpenClaw task with authorization
        result = secure_agent.run(task=task)
        print(f"\n[OpenClaw] Task completed successfully")
        print(f"Return code: {result.get('returncode', 'N/A')}")
        print(f"Output: {result.get('stdout', '')[:200]}...")
    except Exception as e:
        print(f"\n[predicate-secure] Task failed: {e}")


def example_with_debug_mode():
    """Run OpenClaw agent in debug mode for troubleshooting."""
    openclaw_config = OpenClawConfig(skill_proxy_port=8789)

    secure_agent = SecureAgent(
        agent=openclaw_config,
        mode="debug",  # Human-readable trace output
        trace_format="console",
        trace_colors=True,
    )

    print("\n[Debug Mode] Running OpenClaw agent with full tracing...")

    task = "Check if example.com loads correctly"

    try:
        result = secure_agent.run(task=task)
        print("\n[Debug] Task trace complete")
    except Exception as e:
        print(f"\n[Debug] Error occurred: {e}")


def example_with_manual_proxy():
    """
    Example showing how to manually control the proxy lifecycle.

    Useful when you want to keep the proxy running across multiple tasks.
    """
    from predicate_secure.openclaw_adapter import create_openclaw_adapter

    openclaw_config = OpenClawConfig(skill_proxy_port=8790)

    # Create adapter manually
    def authorizer(action: str, context: dict) -> bool:
        """Simple authorizer that allows snapshot but blocks act."""
        if "snapshot" in action:
            return True
        print(f"[Authorizer] Blocked action: {action}")
        return False

    adapter = create_openclaw_adapter(openclaw_config, authorizer=authorizer)

    try:
        # Start proxy (stays running)
        adapter.start_proxy()
        print("[Proxy] Started on http://localhost:8790")

        # Run multiple tasks with same proxy
        tasks = [
            "Take snapshot of example.com",
            "Take snapshot of httpbin.org",
        ]

        for task in tasks:
            print(f"\n[Task] {task}")
            adapter.start_cli(task)
            # Process would run in background
            # In real usage, you'd wait for completion

    finally:
        # Clean up
        adapter.cleanup()
        print("\n[Proxy] Stopped")


if __name__ == "__main__":
    print("=" * 60)
    print("predicate-secure: OpenClaw Agent Example")
    print("=" * 60)

    # Uncomment the example you want to run:

    # Example 1: Basic usage with policy file
    # main()

    # Example 2: Debug mode with full tracing
    # example_with_debug_mode()

    # Example 3: Manual proxy control
    # example_with_manual_proxy()

    print("\nNote: Uncomment one of the example functions in __main__ to run")
    print("Make sure OpenClaw CLI is installed and in your PATH")
