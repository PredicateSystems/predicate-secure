# predicate-secure User Manual

A comprehensive guide to securing your AI agents with predicate-secure.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Framework Guides](#framework-guides)
   - [browser-use](#browser-use)
   - [Playwright](#playwright)
   - [LangChain](#langchain)
   - [PydanticAI](#pydanticai)
5. [Modes](#modes)
6. [Writing Policies](#writing-policies)
7. [Debug Mode](#debug-mode)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

**predicate-secure** is a drop-in security wrapper that adds authorization, verification, and audit capabilities to any AI agent framework. Instead of rewriting your agent code, you simply wrap your existing agent with `SecureAgent` and define a policy file.

### What it does

- **Pre-action authorization** - Every action is checked against your policy before execution
- **Post-execution verification** - Deterministic checks ensure the expected outcome occurred
- **Cryptographic audit** - All decisions are logged with tamper-proof receipts
- **Zero refactoring** - Works with your existing agent code

### How it works

```
Your Agent Code
      │
      ▼
┌─────────────────┐
│  SecureAgent    │
│  ┌───────────┐  │
│  │  Policy   │◀─── Your rules (YAML)
│  │  Engine   │  │
│  └───────────┘  │
│  ┌───────────┐  │
│  │ Snapshot  │◀─── Before/after state
│  │  Engine   │  │
│  └───────────┘  │
│  ┌───────────┐  │
│  │  Audit    │◀─── Decision log
│  │   Log     │  │
│  └───────────┘  │
└─────────────────┘
      │
      ▼
  Execution
```

---

## Installation

### Basic installation

```bash
pip install predicate-secure
```

### With framework-specific extras

```bash
# For browser-use agents
pip install predicate-secure[browser-use]

# For Playwright automation
pip install predicate-secure[playwright]

# For LangChain agents
pip install predicate-secure[langchain]

# Install all extras
pip install predicate-secure[all]
```

### Development installation

```bash
git clone https://github.com/PredicateSystems/py-predicate-secure.git
cd py-predicate-secure
pip install -e ".[dev]"
```

---

## Quick Start

The simplest way to secure your agent is three lines of code:

```python
from predicate_secure import SecureAgent

# 1. Your existing agent (unchanged)
agent = YourAgent(task="Do something", llm=your_model)

# 2. Wrap with SecureAgent
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",  # Your authorization rules
    mode="strict",         # Fail-closed mode
)

# 3. Run with authorization
secure_agent.run()
```

That's it! Every action your agent attempts will now be checked against your policy.

---

## Framework Guides

### browser-use

[browser-use](https://github.com/browser-use/browser-use) is an AI agent framework for browser automation. SecureAgent integrates seamlessly with browser-use agents.

#### Basic Usage

```python
from browser_use import Agent
from langchain_openai import ChatOpenAI
from predicate_secure import SecureAgent

# Create your browser-use agent
llm = ChatOpenAI(model="gpt-4")
agent = Agent(
    task="Buy wireless headphones under $50 on Amazon",
    llm=llm,
)

# Wrap with SecureAgent
secure_agent = SecureAgent(
    agent=agent,
    policy="policies/shopping.yaml",
    mode="strict",
)

# Run the agent
secure_agent.run()
```

#### Policy Example for browser-use

```yaml
# policies/shopping.yaml
rules:
  # Allow browsing Amazon
  - action: "browser.*"
    resource: "https://*.amazon.com/*"
    effect: allow

  # Allow clicking checkout with verification
  - action: "browser.click"
    resource: "*checkout*"
    effect: allow
    require_verification:
      - url_contains: "/checkout"

  # Block external sites
  - action: "browser.navigate"
    resource: "https://external.com/*"
    effect: deny

  # Default deny
  - action: "*"
    resource: "*"
    effect: deny
```

#### Using the Plugin API

For more control, you can use the PredicateBrowserUsePlugin directly:

```python
secure_agent = SecureAgent(agent=agent, policy="policy.yaml")

# Get the plugin for lifecycle hooks
plugin = secure_agent.get_browser_use_plugin()

# Run with lifecycle callbacks
result = await agent.run(
    on_step_start=plugin.on_step_start,
    on_step_end=plugin.on_step_end,
)
```

**Full example:** [examples/browser_use_checkout.py](../examples/browser_use_checkout.py)

---

### Playwright

[Playwright](https://playwright.dev/python/) is a browser automation library. SecureAgent can wrap Playwright pages to add authorization.

#### Basic Usage

```python
from playwright.async_api import async_playwright
from predicate_secure import SecureAgent

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()

    # Wrap the page with SecureAgent
    secure_agent = SecureAgent(
        agent=page,
        policy="policies/form.yaml",
        mode="strict",
    )

    # Use the page as normal
    await page.goto("https://example.com/form")
    await page.fill("#email", "user@example.com")
```

#### Getting AgentRuntime

For advanced use cases with the predicate SDK:

```python
secure_agent = SecureAgent(agent=page, policy="policy.yaml")

# Get the AgentRuntime
runtime = await secure_agent.get_runtime_async()

# Get the pre-action authorizer
authorizer = secure_agent.get_pre_action_authorizer()

# Use with RuntimeAgent
from predicate.runtime_agent import RuntimeAgent
runtime_agent = RuntimeAgent(
    runtime=runtime,
    executor=my_llm,
    pre_action_authorizer=authorizer,
)
```

**Full example:** [examples/playwright_form_fill.py](../examples/playwright_form_fill.py)

---

### LangChain

[LangChain](https://www.langchain.com/) is a framework for building LLM applications. SecureAgent can wrap LangChain agents to authorize tool calls.

#### Basic Usage

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from predicate_secure import SecureAgent

# Create your LangChain agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Wrap with SecureAgent
secure_agent = SecureAgent(
    agent=agent_executor,
    policy="policies/tools.yaml",
    mode="strict",
)

# Run the agent
result = agent_executor.invoke({"input": "Search for AI news"})
```

#### Policy Example for LangChain

```yaml
# policies/tools.yaml
rules:
  # Allow search and calculator
  - action: "tool.search"
    resource: "*"
    effect: allow

  - action: "tool.calculator"
    resource: "*"
    effect: allow

  # Block file operations
  - action: "tool.file_write"
    resource: "*"
    effect: deny

  # Block shell commands
  - action: "tool.shell"
    resource: "*"
    effect: deny

  # Default deny
  - action: "*"
    resource: "*"
    effect: deny
```

#### Using SentienceLangChainCore

For browser-enabled LangChain agents:

```python
secure_agent = SecureAgent(agent=agent_executor, policy="policy.yaml")

# Get the core with browser context
core = secure_agent.get_langchain_core(browser=browser)

# Use core for tool interception
```

**Full example:** [examples/langchain_tool_guard.py](../examples/langchain_tool_guard.py)

---

### PydanticAI

[PydanticAI](https://github.com/pydantic/pydantic-ai) is a framework for building AI agents with Pydantic. SecureAgent supports PydanticAI agents.

#### Basic Usage

```python
from pydantic_ai import Agent
from predicate_secure import SecureAgent

# Create your PydanticAI agent
agent = Agent(model="gpt-4")

# Wrap with SecureAgent
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="strict",
)
```

---

## Modes

SecureAgent supports four execution modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `strict` | Fail-closed: deny action if policy check fails | Production deployments |
| `permissive` | Log but don't block unauthorized actions | Development/testing |
| `debug` | Human-readable trace output | Troubleshooting |
| `audit` | Record decisions without enforcement | Compliance monitoring |

### Strict Mode (default)

```python
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="strict",  # Actions denied by policy will raise an exception
)
```

If an action is denied, `AuthorizationDenied` is raised:

```python
from predicate_secure import AuthorizationDenied

try:
    secure_agent.run()
except AuthorizationDenied as e:
    print(f"Action blocked: {e}")
    print(f"Decision: {e.decision}")
```

### Permissive Mode

```python
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="permissive",  # Log unauthorized actions but don't block
)
```

### Debug Mode

```python
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="debug",  # Show detailed trace output
)
```

### Audit Mode

```python
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="audit",  # Record all decisions without blocking
)
```

---

## Writing Policies

Policies are YAML files that define what actions your agent can perform.

### Basic Structure

```yaml
rules:
  - action: "<action_pattern>"
    resource: "<resource_pattern>"
    effect: allow | deny
    require_verification:  # optional
      - <predicate>
```

### Action Patterns

Actions represent what the agent is trying to do:

| Pattern | Matches | Example |
|---------|---------|---------|
| `browser.click` | Specific action | Only click events |
| `browser.*` | Action prefix | All browser actions |
| `tool.search` | Tool call | Search tool invocation |
| `api.call` | API request | HTTP API calls |
| `*` | Everything | Catch-all rule |

### Resource Patterns

Resources represent what the agent is acting on:

| Pattern | Matches | Example |
|---------|---------|---------|
| `https://example.com/*` | URL prefix | All pages on domain |
| `*checkout*` | Contains text | Any checkout URL |
| `button#submit` | CSS selector | Specific element |
| `/safe/path/*` | File path prefix | Safe directory |
| `*` | Everything | Catch-all |

### Verification Predicates

Predicates ensure the action had the expected effect:

```yaml
require_verification:
  # URL checks
  - url_contains: "/checkout"
  - url_matches: "^https://.*\\.example\\.com/.*"

  # DOM checks
  - element_exists: "#cart-items"
  - element_text_contains:
      selector: ".total"
      text: "$"

  # Custom predicates
  - predicate: "cart_not_empty"
```

### Rule Order

Rules are evaluated top-to-bottom. The first matching rule wins:

```yaml
rules:
  # Specific rules first
  - action: "browser.click"
    resource: "*checkout*"
    effect: allow

  # General rules after
  - action: "browser.*"
    resource: "https://example.com/*"
    effect: allow

  # Default deny last
  - action: "*"
    resource: "*"
    effect: deny
```

### Complete Policy Example

```yaml
# policies/shopping.yaml
#
# Policy for an e-commerce shopping agent

rules:
  # Allow browsing the store
  - action: "browser.navigate"
    resource: "https://*.amazon.com/*"
    effect: allow

  - action: "browser.click"
    resource: "https://*.amazon.com/*"
    effect: allow

  - action: "browser.fill"
    resource: "https://*.amazon.com/*"
    effect: allow

  # Allow checkout with verification
  - action: "browser.click"
    resource: "*place-order*"
    effect: allow
    require_verification:
      - url_contains: "/checkout"
      - element_exists: "#cart-items"

  # Block navigation to external sites
  - action: "browser.navigate"
    resource: "https://malicious.com/*"
    effect: deny

  # Block sensitive actions
  - action: "browser.fill"
    resource: "*password*"
    effect: deny

  # Default: deny everything else
  - action: "*"
    resource: "*"
    effect: deny
```

---

## Debug Mode

Debug mode provides detailed trace output for troubleshooting agent behavior.

### Enabling Debug Mode

```python
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="debug",
)
```

### Trace Output Options

```python
secure_agent = SecureAgent(
    agent=agent,
    mode="debug",
    trace_format="console",  # "console" or "json"
    trace_file="trace.jsonl", # Optional file output
    trace_colors=True,        # ANSI colors (console only)
    trace_verbose=True,       # Verbose output
)
```

### Console Output Example

```
============================================================
[predicate-secure] Session Start
  Framework: browser_use
  Mode: debug
  Policy: policy.yaml
  Principal: agent:default
============================================================

[Step 1] navigate → https://amazon.com
  └─ OK (45ms)

[Step 2] search → wireless headphones
  └─ OK (120ms)

[Step 3] click → add-to-cart-button
  ├─ Policy: ALLOWED
  │  Action: browser.click
  │  Resource: add-to-cart-button
  ├─ Cart Update:
  │  + cart_item_1
  │  ~ cart_count
  │    Before: 0
  │    After:  1
  ├─ Verification: PASS
  │  Predicate: cart_not_empty
  │  Message: Cart has 1 item
  └─ OK (85ms)

============================================================
[predicate-secure] Session End: SUCCESS
  Total Steps: 3
  Duration: 250ms
============================================================
```

### JSON Trace Output

```python
secure_agent = SecureAgent(
    agent=agent,
    mode="debug",
    trace_format="json",
    trace_file="trace.jsonl",
)
```

Output (one JSON object per line):

```json
{"event_type": "session_start", "timestamp": "2024-01-01T00:00:00Z", "data": {"framework": "browser_use", "mode": "debug"}}
{"event_type": "step_start", "timestamp": "2024-01-01T00:00:01Z", "step_number": 1, "data": {"action": "navigate", "resource": "https://amazon.com"}}
{"event_type": "step_end", "timestamp": "2024-01-01T00:00:02Z", "step_number": 1, "duration_ms": 1000, "data": {"success": true}}
```

### Manual Tracing

You can add custom trace points in your code:

```python
# Trace a step
step = secure_agent.trace_step("custom_action", "custom_resource")
# ... do something ...
secure_agent.trace_step_end(step, success=True)

# Trace a state change
secure_agent.trace_snapshot_diff(
    before={"cart": []},
    after={"cart": ["item1"]},
    label="Cart Updated",
)

# Trace a verification
secure_agent.trace_verification(
    predicate="items_in_cart",
    passed=True,
    message="Cart has expected items",
)
```

---

## Advanced Usage

### Getting the Pre-Action Authorizer

For direct integration with RuntimeAgent:

```python
secure_agent = SecureAgent(agent=agent, policy="policy.yaml")

# Get the authorizer callback
authorizer = secure_agent.get_pre_action_authorizer()

# Use with RuntimeAgent
from predicate.runtime_agent import RuntimeAgent
runtime_agent = RuntimeAgent(
    runtime=runtime,
    executor=my_llm,
    pre_action_authorizer=authorizer,
)
```

### Getting Adapters

Access the full adapter for any framework:

```python
secure_agent = SecureAgent(agent=agent, policy="policy.yaml")

# Get adapter with all wired components
adapter = secure_agent.get_adapter()

print(adapter.agent_runtime)  # AgentRuntime instance
print(adapter.backend)        # Backend for DOM interaction
print(adapter.plugin)         # Framework-specific plugin
print(adapter.executor)       # LLM executor
print(adapter.metadata)       # Framework info
```

### Attach Pattern

Alternative way to create SecureAgent:

```python
# Factory method
secure_agent = SecureAgent.attach(
    agent,
    policy="policy.yaml",
    mode="strict",
)
```

### Environment Variables

You can configure SecureAgent via environment variables:

| Variable | Description |
|----------|-------------|
| `PREDICATE_AUTHORITY_POLICY_FILE` | Default policy file path |
| `PREDICATE_PRINCIPAL_ID` | Default agent principal ID |
| `PREDICATE_AUTHORITY_SIGNING_KEY` | Signing key for mandates |

---

## Troubleshooting

### Common Issues

#### "AuthorizationDenied: Action denied"

Your policy is blocking the action. Check:

1. Is the action pattern correct?
2. Is the resource pattern matching?
3. Are rules in the right order (specific before general)?

Debug with:

```python
secure_agent = SecureAgent(agent=agent, policy="policy.yaml", mode="debug")
```

#### "UnsupportedFrameworkError"

SecureAgent couldn't detect your agent's framework. Make sure you're using a supported framework:

- browser-use Agent
- Playwright Page (sync or async)
- LangChain AgentExecutor
- PydanticAI Agent

#### "PolicyLoadError"

The policy file couldn't be loaded. Check:

1. File path is correct
2. YAML syntax is valid
3. Required fields are present

#### Import Errors

Make sure you have the correct extras installed:

```bash
pip install predicate-secure[browser-use]  # For browser-use
pip install predicate-secure[playwright]   # For Playwright
pip install predicate-secure[langchain]    # For LangChain
```

### Getting Help

- GitHub Issues: https://github.com/PredicateSystems/py-predicate-secure/issues
- Documentation: https://predicate.systems/docs

---

## API Reference

### SecureAgent

```python
class SecureAgent:
    def __init__(
        self,
        agent: Any,
        policy: str | Path | None = None,
        mode: str = "strict",
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
    ): ...

    # Properties
    @property
    def config(self) -> SecureAgentConfig: ...
    @property
    def wrapped(self) -> WrappedAgent: ...
    @property
    def framework(self) -> Framework: ...
    @property
    def tracer(self) -> DebugTracer | None: ...

    # Methods
    def run(self, task: str | None = None) -> Any: ...
    def get_pre_action_authorizer(self) -> Callable: ...
    def get_adapter(self, **kwargs) -> AdapterResult: ...
    async def get_runtime_async(self, **kwargs) -> AgentRuntime: ...
    def get_browser_use_plugin(self, **kwargs) -> PredicateBrowserUsePlugin: ...
    def get_langchain_core(self, **kwargs) -> SentienceLangChainCore: ...

    # Tracing
    def trace_step(self, action: str, resource: str = "") -> int | None: ...
    def trace_step_end(self, step_number: int, success: bool = True, **kwargs) -> None: ...
    def trace_snapshot_diff(self, before: dict, after: dict, label: str = "") -> None: ...
    def trace_verification(self, predicate: str, passed: bool, **kwargs) -> None: ...
```

### Exceptions

```python
class AuthorizationDenied(Exception):
    decision: Any  # The authorization decision

class VerificationFailed(Exception):
    predicate: str  # The failed predicate

class PolicyLoadError(Exception):
    pass

class UnsupportedFrameworkError(Exception):
    pass
```

### Modes

```python
MODE_STRICT = "strict"
MODE_PERMISSIVE = "permissive"
MODE_DEBUG = "debug"
MODE_AUDIT = "audit"
```
