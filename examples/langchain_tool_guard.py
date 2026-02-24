"""
LangChain tool interception with predicate-secure.

This example demonstrates:
- Wrapping a LangChain AgentExecutor with SecureAgent
- Policy-based authorization for tool calls
- Getting SentienceLangChainCore for tool interception
- Debug mode for troubleshooting

Requirements:
    pip install predicate-secure[langchain]
    pip install langchain langchain-openai
"""

import tempfile

from predicate_secure import SecureAgent

# Uncomment for actual LangChain usage
# from langchain.agents import AgentExecutor, create_react_agent
# from langchain_openai import ChatOpenAI
# from langchain.tools import Tool


def create_tool_policy() -> str:
    """Create a tool authorization policy."""
    policy_content = """
# Tool authorization policy
rules:
  # Allow search tool
  - action: "tool.search"
    resource: "*"
    effect: allow

  # Allow calculator tool
  - action: "tool.calculator"
    resource: "*"
    effect: allow

  # Allow file read (read-only)
  - action: "tool.file_read"
    resource: "/safe/path/*"
    effect: allow

  # Block file write
  - action: "tool.file_write"
    resource: "*"
    effect: deny

  # Block shell commands
  - action: "tool.shell"
    resource: "*"
    effect: deny

  # Block network requests to untrusted domains
  - action: "tool.http_request"
    resource: "https://untrusted.com/*"
    effect: deny

  # Allow API calls to trusted services
  - action: "tool.http_request"
    resource: "https://api.trusted.com/*"
    effect: allow

  # Default: deny
  - action: "*"
    resource: "*"
    effect: deny
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="_tool_policy.yaml", delete=False) as f:
        f.write(policy_content)
        return f.name


def run_secure_tool_agent():
    """Run a secure LangChain agent with tool interception."""

    policy_path = create_tool_policy()

    # Mock LangChain AgentExecutor for demonstration
    # In real usage:
    #
    # llm = ChatOpenAI(model="gpt-4")
    # tools = [search_tool, calculator_tool]
    # agent = create_react_agent(llm, tools, prompt)
    # agent_executor = AgentExecutor(agent=agent, tools=tools)
    #
    # secure_agent = SecureAgent(
    #     agent=agent_executor,
    #     policy=policy_path,
    #     mode="strict",
    # )

    class MockAgentExecutor:
        """Mock LangChain AgentExecutor for demonstration."""

        __module__ = "langchain.agents.executor"

        def __init__(self):
            self.llm = "gpt-4"
            self.tools = ["search", "calculator", "file_read"]

        def invoke(self, inputs: dict):
            print(f"Mock: invoke({inputs})")
            return {"output": "Mock result"}

    # Create mock executor
    agent_executor = MockAgentExecutor()

    # Wrap with SecureAgent
    secure_agent = SecureAgent(
        agent=agent_executor,
        policy=policy_path,
        mode="debug",
        trace_format="console",
        principal_id="langchain-agent:tools",
    )

    print(f"Created: {secure_agent}")
    print(f"Framework: {secure_agent.framework}")
    print(f"Executor: {secure_agent.wrapped.executor}")
    print()

    # Demonstrate tracing for tool calls
    step = secure_agent.trace_step("tool.search", "query='AI news'")
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("tool.calculator", "2 + 2")
    secure_agent.trace_step_end(step, success=True)

    step = secure_agent.trace_step("tool.file_write", "/etc/passwd")
    secure_agent.trace_step_end(step, success=False, error="Action denied by policy")

    secure_agent.trace_verification(
        predicate="no_dangerous_tools",
        passed=True,
        message="All tool calls were safe",
    )

    print("\nTool interception flow traced successfully!")


def demonstrate_langchain_core():
    """Demonstrate getting SentienceLangChainCore for advanced usage."""
    print("\n" + "=" * 60)
    print("Advanced: Getting SentienceLangChainCore")
    print("=" * 60 + "\n")

    class MockAgentExecutor:
        __module__ = "langchain.agents.executor"

        def __init__(self):
            self.llm = "gpt-4"

    agent_executor = MockAgentExecutor()

    secure_agent = SecureAgent(
        agent=agent_executor,
        mode="strict",
    )

    print(f"Framework: {secure_agent.framework}")
    print()

    # Without browser, get_langchain_core returns None
    core = secure_agent.get_langchain_core()
    print(f"Without browser: core = {core}")
    print()

    # With browser (for browser-enabled LangChain agents):
    print("With browser (requires predicate SDK):")
    print("  core = secure_agent.get_langchain_core(browser=browser)")
    print("  # Use core for tool interception")
    print()

    # In real usage with browser:
    # from playwright.async_api import async_playwright
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch()
    #     core = secure_agent.get_langchain_core(browser=browser)


def demonstrate_adapter():
    """Demonstrate using the adapter API."""
    print("\n" + "=" * 60)
    print("Advanced: Using Adapter API")
    print("=" * 60 + "\n")

    class MockAgentExecutor:
        __module__ = "langchain.agents.executor"

        def __init__(self):
            self.llm = "gpt-4"

    agent_executor = MockAgentExecutor()

    secure_agent = SecureAgent(
        agent=agent_executor,
        mode="strict",
    )

    # Get adapter for the agent
    # This provides access to all wired components
    try:
        adapter = secure_agent.get_adapter()
        print(f"Adapter metadata: {adapter.metadata}")
        print(f"Executor: {adapter.executor}")
        print(f"Plugin: {adapter.plugin}")
    except Exception as e:
        print(f"Adapter requires predicate SDK: {e}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("LangChain Tool Guard with predicate-secure")
    print("=" * 60)
    print()

    run_secure_tool_agent()
    demonstrate_langchain_core()
    demonstrate_adapter()


if __name__ == "__main__":
    main()
