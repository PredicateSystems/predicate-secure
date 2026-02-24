"""
Form automation with Playwright and predicate-secure.

This example demonstrates:
- Wrapping a Playwright page with SecureAgent
- Policy-based authorization for form actions
- Debug mode tracing
- Getting AgentRuntime for advanced use cases

Requirements:
    pip install predicate-secure[playwright]
    playwright install chromium
"""

import asyncio
import tempfile

from predicate_secure import SecureAgent

# Uncomment for actual Playwright usage
# from playwright.async_api import async_playwright


def create_form_policy() -> str:
    """Create a form automation policy file."""
    policy_content = """
# Form automation policy
rules:
  # Allow filling form fields
  - action: "browser.fill"
    resource: "input[type='text']"
    effect: allow

  - action: "browser.fill"
    resource: "input[type='email']"
    effect: allow

  # Allow clicking submit buttons
  - action: "browser.click"
    resource: "button[type='submit']"
    effect: allow
    require_verification:
      - element_exists: "form"

  # Allow navigation to form pages
  - action: "browser.navigate"
    resource: "https://example.com/form*"
    effect: allow

  # Block sensitive actions
  - action: "browser.fill"
    resource: "input[type='password']"
    effect: deny

  # Default deny
  - action: "*"
    resource: "*"
    effect: deny
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_form_policy.yaml", delete=False
    ) as f:
        f.write(policy_content)
        return f.name


async def run_secure_form_fill():
    """Run a secure form fill automation."""

    policy_path = create_form_policy()

    # Mock Playwright page for demonstration
    # In real usage:
    #
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch()
    #     page = await browser.new_page()
    #     await page.goto("https://example.com/form")
    #
    #     secure_agent = SecureAgent(
    #         agent=page,
    #         policy=policy_path,
    #         mode="debug",
    #     )

    class MockPlaywrightPage:
        """Mock Playwright page for demonstration."""

        __module__ = "playwright.async_api._generated"

        async def fill(self, selector: str, value: str):
            print(f"Mock: fill({selector}, {value})")

        async def click(self, selector: str):
            print(f"Mock: click({selector})")

        async def goto(self, url: str):
            print(f"Mock: goto({url})")

    # Create mock page
    page = MockPlaywrightPage()

    # Wrap with SecureAgent
    secure_agent = SecureAgent(
        agent=page,
        policy=policy_path,
        mode="debug",
        trace_format="console",
        principal_id="form-agent:automation",
    )

    print(f"Created: {secure_agent}")
    print(f"Framework: {secure_agent.framework}")
    print()

    # Demonstrate tracing for form fill flow
    step = secure_agent.trace_step("navigate", "https://example.com/form")
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("fill", "input[name='email']")
    secure_agent.trace_snapshot_diff(
        before={"email_field": ""},
        after={"email_field": "user@example.com"},
        label="Form Input",
    )
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("fill", "input[name='name']")
    secure_agent.trace_snapshot_diff(
        before={"name_field": ""},
        after={"name_field": "John Doe"},
        label="Form Input",
    )
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("click", "button[type='submit']")
    secure_agent.trace_verification(
        predicate="form_valid",
        passed=True,
        message="All required fields filled",
    )
    secure_agent.trace_step_end(step, success=True)

    print("\nForm fill flow traced successfully!")


async def run_with_runtime():
    """Demonstrate getting AgentRuntime for advanced usage."""
    print("\n" + "=" * 60)
    print("Advanced: Getting AgentRuntime")
    print("=" * 60 + "\n")

    # This shows how to get the AgentRuntime for advanced use cases
    # like using RuntimeAgent directly

    class MockPlaywrightPage:
        __module__ = "playwright.async_api._generated"

    page = MockPlaywrightPage()

    secure_agent = SecureAgent(
        agent=page,
        mode="strict",
    )

    print(f"Framework: {secure_agent.framework}")
    print("To get AgentRuntime (requires predicate SDK):")
    print("  runtime = await secure_agent.get_runtime_async()")
    print("  authorizer = secure_agent.get_pre_action_authorizer()")
    print()

    # In real usage:
    # runtime = await secure_agent.get_runtime_async()
    # from predicate.runtime_agent import RuntimeAgent
    # runtime_agent = RuntimeAgent(
    #     runtime=runtime,
    #     executor=my_llm,
    #     pre_action_authorizer=secure_agent.get_pre_action_authorizer(),
    # )


def main():
    """Main entry point."""
    print("=" * 60)
    print("Form Automation with predicate-secure")
    print("=" * 60)
    print()

    asyncio.run(run_secure_form_fill())
    asyncio.run(run_with_runtime())


if __name__ == "__main__":
    main()
