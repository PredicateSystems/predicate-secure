# predicate-secure

[![License](https://img.shields.io/badge/License-MIT%2FApache--2.0-blue.svg)](LICENSE)
[![PyPI - predicate-secure](https://img.shields.io/pypi/v/predicate-secure.svg)](https://pypi.org/project/predicate-secure/)

Drop-in security wrapper for AI agents. Adds authorization, verification, and audit to any agent framework in 3 lines of code.

## Features

- **Pre-action authorization** - Policy engine gates every action before execution
- **Post-execution verification** - Deterministic predicate checks (no LLM-as-a-judge)
- **Cryptographic audit** - WORM-ready receipts linking intent to outcome
- **Zero refactoring** - Wrap your existing agent, keep your framework

## Installation

```bash
pip install predicate-secure
```

With framework-specific extras:

```bash
pip install predicate-secure[browser-use]
pip install predicate-secure[langchain]
pip install predicate-secure[playwright]
pip install predicate-secure[all]
```

## Quick Start

```python
from predicate_secure import SecureAgent
from browser_use import Agent

# 1. Your existing agent (unchanged)
agent = Agent(task="Buy headphones on Amazon", llm=my_model)

# 2. Wrap with SecureAgent
secure_agent = SecureAgent(
    agent=agent,
    policy="policies/shopping.yaml",
    mode="strict",
)

# 3. Run with full authorization + verification
secure_agent.run()
```

## Modes

| Mode | Behavior |
|------|----------|
| `strict` | Fail-closed: deny action if policy check fails |
| `permissive` | Log but don't block unauthorized actions |
| `debug` | Human-readable trace output for debugging |
| `audit` | Record decisions without enforcement |

## Supported Frameworks

| Framework | Status |
|-----------|--------|
| browser-use | Supported |
| LangChain | Supported |
| Playwright | Supported |
| PydanticAI | Supported |
| OpenClaw | Planned |

## Architecture

`predicate-secure` is a thin orchestration layer that combines:

- **[predicate-runtime](https://github.com/PredicateSystems/sdk-python)** - Snapshot engine, DOM pruning, verification predicates
- **[predicate-authority](https://github.com/PredicateSystems/predicate-authority)** - Policy engine, mandate signing, audit logging

```
SecureAgent
    ├── AgentRuntime (snapshot, assertions)
    ├── AuthorityClient (policy, mandates)
    └── RuntimeAgent (orchestration, pre-action hook)
```

## Debug Mode

Debug mode provides human-readable trace output for troubleshooting:

```python
secure_agent = SecureAgent(
    agent=agent,
    policy="policy.yaml",
    mode="debug",
    trace_format="console",  # or "json"
    trace_file="trace.jsonl",  # optional file output
)
```

Console output shows:
- Session start/end with framework and policy info
- Each step with action and resource
- Policy decisions (ALLOWED/DENIED) with reason codes
- Snapshot diffs (before/after state changes)
- Verification results (PASS/FAIL)

For JSON trace output (machine-parseable):

```python
secure_agent = SecureAgent(
    agent=agent,
    mode="debug",
    trace_format="json",
    trace_file="trace.jsonl",
)
```

## Policy Reference

### Basic Structure

```yaml
# policies/example.yaml
rules:
  - action: "<action_pattern>"
    resource: "<resource_pattern>"
    effect: allow | deny
    require_verification:  # optional
      - <predicate>
```

### Action Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `browser.*` | All browser actions | click, type, navigate |
| `browser.click` | Specific action | Only click events |
| `api.call` | API tool calls | HTTP requests |
| `*` | Wildcard (all actions) | Catch-all rules |

### Resource Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `https://example.com/*` | URL prefix match | All pages on domain |
| `*checkout*` | Contains match | Any checkout-related URL |
| `button#submit` | CSS selector | Specific element |
| `*` | Wildcard (all resources) | Catch-all |

### Verification Predicates

```yaml
require_verification:
  # URL checks
  - url_contains: "/checkout"
  - url_matches: "^https://.*\\.amazon\\.com/.*"

  # DOM state checks
  - element_exists: "#cart-items"
  - element_text_contains:
      selector: ".total"
      text: "$"

  # Custom predicates
  - predicate: "cart_not_empty"
```

### Policy Example

```yaml
# policies/shopping.yaml
rules:
  # Allow browsing Amazon
  - action: "browser.*"
    resource: "https://amazon.com/*"
    effect: allow

  # Allow checkout with verification
  - action: "browser.click"
    resource: "*checkout*"
    effect: allow
    require_verification:
      - url_contains: "/checkout"
      - element_exists: "#cart-items"

  # Block external links
  - action: "browser.navigate"
    resource: "https://external.com/*"
    effect: deny

  # Default deny
  - action: "*"
    resource: "*"
    effect: deny
```

## Development

```bash
# Install dev dependencies
make dev-install

# Install pre-commit hooks
make hooks

# Run tests
make test

# Run linters
make lint
```

## License

Dual-licensed under MIT or Apache-2.0. See [LICENSE](./LICENSE).
