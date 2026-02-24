"""
E-commerce checkout flow with browser-use and predicate-secure.

This example demonstrates:
- Wrapping a browser-use Agent with SecureAgent
- Policy-based authorization for browser actions
- Debug mode for troubleshooting
- Verification predicates for checkout flow

Requirements:
    pip install predicate-secure[browser-use]
    # Set up your LLM (e.g., OpenAI API key)
"""

import asyncio
import tempfile

from predicate_secure import SecureAgent

# Uncomment to use with actual browser-use
# from browser_use import Agent
# from langchain_openai import ChatOpenAI


def create_shopping_policy() -> str:
    """Create a shopping policy file and return the path."""
    policy_content = """
# Shopping policy - controls what the agent can do during checkout
rules:
  # Allow browsing and interacting with Amazon
  - action: "browser.*"
    resource: "https://*.amazon.com/*"
    effect: allow

  # Allow clicking checkout buttons with verification
  - action: "browser.click"
    resource: "*checkout*"
    effect: allow
    require_verification:
      - url_contains: "/checkout"

  # Allow clicking add-to-cart buttons
  - action: "browser.click"
    resource: "*add-to-cart*"
    effect: allow

  # Allow form filling for shipping/payment
  - action: "browser.fill"
    resource: "*address*"
    effect: allow

  # Block navigation to external sites
  - action: "browser.navigate"
    resource: "https://external-site.com/*"
    effect: deny

  # Default: deny everything else
  - action: "*"
    resource: "*"
    effect: deny
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="_shopping_policy.yaml", delete=False) as f:
        f.write(policy_content)
        return f.name


async def run_secure_checkout():
    """Run a secure e-commerce checkout flow."""

    # Create policy file
    policy_path = create_shopping_policy()

    # Example with mock agent (for demonstration)
    # In real usage, replace with actual browser-use Agent:
    #
    # llm = ChatOpenAI(model="gpt-4")
    # agent = Agent(
    #     task="Buy wireless headphones under $50 on Amazon",
    #     llm=llm,
    # )

    class MockBrowserUseAgent:
        """Mock agent for demonstration purposes."""

        __module__ = "browser_use.agent"

        def __init__(self):
            self.task = "Buy wireless headphones under $50 on Amazon"
            self.llm = "mock_llm"
            self.browser = MockBrowser()

        async def run(self):
            print("Mock agent: Would browse Amazon and add item to cart")
            return {"status": "completed", "item": "Sony WH-1000XM4"}

    class MockBrowser:
        """Mock browser session."""

        pass

    # Create mock agent
    agent = MockBrowserUseAgent()

    # Wrap with SecureAgent for authorization + verification
    secure_agent = SecureAgent(
        agent=agent,
        policy=policy_path,
        mode="debug",  # Enable debug output
        trace_format="console",
        principal_id="shopping-agent:checkout",
    )

    print(f"Created: {secure_agent}")
    print(f"Framework: {secure_agent.framework}")
    print(f"Policy: {policy_path}")
    print()

    # Manual step tracing (for demonstration)
    step = secure_agent.trace_step("navigate", "https://amazon.com")
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("search", "wireless headphones")
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("click", "add-to-cart-button")
    secure_agent.trace_snapshot_diff(
        before={"cart_count": 0},
        after={"cart_count": 1},
        label="Cart Update",
    )
    secure_agent.trace_step_end(step, success=True)

    secure_agent.trace_verification(
        predicate="cart_not_empty",
        passed=True,
        message="Cart has 1 item",
    )

    print("\nCheckout flow traced successfully!")
    print("In production, use secure_agent.run() to execute the full flow.")


def main():
    """Main entry point."""
    print("=" * 60)
    print("E-commerce Checkout with predicate-secure")
    print("=" * 60)
    print()

    asyncio.run(run_secure_checkout())


if __name__ == "__main__":
    main()
