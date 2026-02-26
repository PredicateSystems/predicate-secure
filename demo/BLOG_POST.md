# Building Trustworthy AI Agents: Predicate Secure Demo

**Category:** Engineering
**Date:** February 25, 2026
**Read Time:** 12 min read

AI agents are powerful, but how do you ensure they don't go rogue? Today we're releasing **Predicate Secure** - a drop-in security wrapper that adds enterprise-grade authorization and verification to browser automation agents. Think of it as a safety harness for your AI agents.

**Predicate Secure integrates with your existing AI agent frameworks in just 3-5 lines of code** - including browser-use, LangChain, PydanticAI, raw Playwright, and OpenClaw. This frictionless adoption means you can add robust security without rewriting your agents.

This post walks through our comprehensive demo that showcases the complete agent security loop: pre-execution authorization, browser automation, and post-execution verification using local LLMs.

## The Challenge: Trustworthy Agent Automation

When AI agents interact with browsers and web services, they need guardrails. A misconfigured prompt or unexpected model behavior could lead to:

- Navigating to unauthorized domains
- Clicking sensitive buttons or forms
- Exposing credentials or API keys
- Executing actions outside policy boundaries

Traditional approaches rely on prompt engineering or hope for the best. **Predicate Secure takes a different approach**: enforce policy before execution, verify outcomes after.

## The Solution: Complete Deterministic Agent Loop

Predicate Secure implements a **complete three-phase agent loop** that combines:

1. **Pre-execution authorization** - Deterministic policy-based decisions
2. **Action execution** - Controlled browser automation
3. **Post-execution verification** - Deterministic assertion checking

This is **not a probabilistic safety approach**. Every action is governed by explicit policy rules (deterministic authorization) and validated against concrete predicates (deterministic verification). The LLM's role is constrained to generating verification predicates based on observed state changes - the actual verification execution is deterministic.

### Three-Phase Security Model

**Phase 1: Pre-Execution Authorization**
- Policy-based decision: Is this action allowed?
- Deterministic rule evaluation

**Phase 2: Action Execution**
- Browser automation with snapshot capture
- Controlled execution environment

**Phase 3: Post-Execution Verification**
- LLM-generated assertions validate outcomes
- Deterministic predicate evaluation

## Demo Architecture

The demo showcases a complete end-to-end implementation with:

- **0 External Dependencies** - 100% offline capable
- **Free** - Local LLM verification

### Core Components

**1. Predicate Runtime SDK** (`predicate-runtime==1.1.2`)
- Browser automation via AsyncPredicateBrowser
- Semantic element detection with `find()` DSL
- Visual overlay for element highlighting
- Automatic Chrome extension injection

**2. Predicate Authority** (`predicate-authority>=0.1.0`)
- YAML-based policy enforcement
- Fail-closed authorization (deny by default)
- Optional Rust-based sidecar for production
- Flexible identity: Local IdP, Okta, Entra ID (Azure AD), OIDC

**3. Local LLM Verification** (Qwen 2.5 7B Instruct)
- Generates verification predicates from page state changes
- Runs completely offline on Apple Silicon (MPS)
- ~14GB model, 5-second cold start after initial download

**4. Cloud Tracing** (Optional)
- Upload authorization and verification events to Predicate Studio
- Visualize execution timeline in web UI
- Track decisions across agent runs

## Frictionless Framework Integration

Predicate Secure wraps your existing agent code in **3-5 lines** - no rewrites needed:

| Framework | Adapter | Integration Effort |
|-----------|---------|-------------------|
| `browser-use` | `BrowserUseAdapter` | 3 lines |
| `LangChain` | `SentienceLangChainCore` | 4 lines |
| `PydanticAI` | `predicate.integrations.pydanticai` | 3 lines |
| `Raw Playwright` | `AgentRuntime.from_playwright_page()` | 5 lines |
| `OpenClaw` | `OpenClawAdapter` | 3 lines |

> **Success:** All adapters are production-ready and maintained in the `predicate-runtime` SDK. Drop-in security for any agent framework.

## What the Demo Does

The demo executes a simple but complete browser task:

✓ Navigate to https://www.example.com with policy check
✓ Take snapshot with visual element overlay
✓ Find and click "Learn more" link using semantic query
✓ Verify URL contains "example-domains" after navigation
✓ Upload trace to Predicate Studio (if API key provided)

Each action goes through the full authorization + verification loop.

## Code Walkthrough

### 1. Semantic Element Finding

Instead of brittle CSS selectors, we use semantic queries:

```python
from predicate import find

# Find link by semantic properties, not CSS
element = find(snapshot, "role=link text~'Learn more'")

if element:
    print(f"Found: {element.text} (ID: {element.id})")
    print(f"Clickable: {element.visual_cues.is_clickable}")
    await click_element(element)
```

The `find()` function understands:
- ARIA roles (`role=link`, `role=button`)
- Text content matching (`text~'substring'`)
- Visual cues (clickability, visibility)
- Element importance ranking

### 2. Authorization Policy

Authorization rules are declarative YAML:

```yaml
# Allow navigation to safe domains
- name: allow-navigation-safe-domains
  effect: ALLOW
  principals:
    - "agent:demo-browser"
  actions:
    - "browser.navigate"
  resources:
    - "https://www.example.com*"
    - "https://www.google.com*"
  conditions:
    required_labels:
      - "browser_initialized"

# Allow clicks on safe element types
- name: allow-browser-click-safe-elements
  effect: ALLOW
  principals:
    - "agent:demo-browser"
  actions:
    - "browser.click"
  resources:
    - "element:role=link[*"
    - "element:role=button[*"
    - "element#*"  # By snapshot ID
  conditions:
    required_labels:
      - "element_visible"
      - "snapshot_captured"

# Default deny (fail-closed)
- name: default-deny
  effect: DENY
  principals:
    - "*"
  actions:
    - "*"
  resources:
    - "*"
```

> **Note:** The policy is fail-closed: any action not explicitly allowed is denied. This prevents agents from taking unexpected actions.

### 3. Verification with Local LLM

After each action, the local LLM generates verification predicates:

```python
# Capture pre and post snapshots
pre_snapshot = await get_page_summary()
result = await execute_action()
post_snapshot = await get_page_summary()

# LLM generates verification plan
verification_plan = verifier.generate_verification_plan(
    action="click",
    action_target="element#6",
    pre_snapshot_summary=pre_snapshot,
    post_snapshot_summary=post_snapshot,
    context={"task": "Find and click Learn more link"}
)

# Execute generated verifications
for verification in verification_plan.verifications:
    passed = execute_predicate(
        verification.predicate,  # e.g., "url_contains"
        verification.args         # e.g., ["example-domains"]
    )

    if not passed:
        raise AssertionError("Post-execution verification failed")
```

The LLM sees both snapshots and generates appropriate checks:

```json
{
  "verifications": [
    {
      "predicate": "url_contains",
      "args": ["example-domains"]
    },
    {
      "predicate": "snapshot_changed",
      "args": []
    }
  ],
  "reasoning": "Verify navigation by checking URL change and snapshot difference."
}
```

### 4. Visual Element Overlay

Enable visual debugging with snapshot overlays:

```python
from predicate.snapshot import snapshot_async
from predicate.models import SnapshotOptions

snap = await snapshot_async(
    browser,
    SnapshotOptions(
        show_overlay=True,  # Highlights detected elements in browser
        screenshot=False,
    ),
)

print(f"Captured {len(snap.elements)} elements")
# Watch the browser - you'll see colored boxes around detected elements!
```

This is invaluable for debugging why an agent can't find an element.

## Real Demo Output

Here's what the demo produces when run:

```
╭──────────────── Demo Configuration ─────────────────╮
│ Predicate Secure Browser Automation Demo            │
│ Task: Navigate to example.com and verify page loads │
│ Start URL: https://www.example.com                  │
│ Principal: agent:demo-browser                       │
╰─────────────────────────────────────────────────────╯

Initializing Local LLM Verifier...
⠋ Loading Qwen 2.5 7B model...
✓ Verifier initialized

Initializing Cloud Tracer...
☁️  Cloud tracing enabled (Pro tier)
✓ Cloud tracer initialized
  Run ID: 777c0308-82c8-454d-98df-5a603d12d418
  View trace: https://studio.predicatesystems.dev/runs/...

Step 1: Initializing Browser...
✓ Browser started

Step 2: Executing Browser Task...

→ Action: navigate (https://www.example.com)
  Pre-execution: Checking authorization...
  ✓ Action authorized
  Executing action...
  ✓ Action executed
  Post-execution: Generating verification plan...
  i Generated 1 verifications
    Reasoning: Fallback: verify URL changed after navigation
  Executing verifications...
    [1] url_changed()
        ✓ Passed
  ✓ All verifications passed

→ Action: snapshot (current_page)
  Pre-execution: Checking authorization...
  ✓ Action authorized
  Executing action...
    Snapshot captured: 2 elements
    (Watch the browser - elements are highlighted!)
  ✓ Action executed
  Post-execution: Generating verification plan...
  i Generated 1 verifications
    Reasoning: Verify page load by checking URL contains domain.
  Executing verifications...
    [1] url_contains(example.com)
        ✓ Passed
  ✓ All verifications passed

→ Finding link with text: 'Learn more'
  ✓ Found element: Learn more (ID: 6)
    Role: link, Clickable: True

→ Action: click (element#6)
  Pre-execution: Checking authorization...
  ✓ Action authorized
  Executing action...
    Clicked at coordinates: (256.0, 198.078125)
  ✓ Action executed
  Post-execution: Generating verification plan...
  i Generated 2 verifications
    Reasoning: Verify navigation and page load.
  Executing verifications...
    [1] url_contains(example.com)
        ✓ Passed
    [2] snapshot_changed()
        ✓ Passed
  ✓ All verifications passed

✓ Task completed successfully

Cleaning up...
✓ Browser closed
Uploading trace to Predicate Studio...
✅ Trace uploaded successfully
  View in Studio: https://studio.predicatesystems.dev/runs/...
```

## Setup Instructions

### Prerequisites

✓ Python 3.11+ (Python 3.11.9 recommended)
✓ 16GB+ RAM (for 7B model) or 8GB+ (for 3B model)
✓ Apple Silicon Mac (MPS support) or CUDA GPU
✓ 10GB disk space for model files

### Installation (5 minutes)

```bash
# Clone repository
cd /path/to/Sentience/predicate-secure/py-predicate-secure

# Install SDK
pip install -e .

# Install demo dependencies
cd demo
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Configuration

Create a `.env` file in the demo directory:

```bash
# Browser display (false = show browser)
BROWSER_HEADLESS=false

# LLM model for verification
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
LLM_DEVICE=auto  # Automatically detects MPS/CUDA/CPU
LLM_MAX_TOKENS=512
LLM_TEMPERATURE=0.0

# Optional: Predicate API key for cloud tracing
# PREDICATE_API_KEY=your-api-key-here

# Demo configuration
DEMO_START_URL=https://www.example.com
DEMO_TASK_DESCRIPTION=Navigate to example.com and verify page loads
DEMO_PRINCIPAL_ID=agent:demo-browser
```

> **Success:** The demo works completely **offline** (after initial model download). No API key required!

### Running the Demo

```bash
# Simple mode with in-process authorization
python secure_browser_demo.py

# First run: Model downloads automatically (~14GB, 2-5 minutes)
# Subsequent runs: Fast startup (~5 seconds)
```

## Performance Characteristics

Based on real demo runs on Apple Silicon (M-series):

| Metric | Value | Notes |
|--------|-------|-------|
| Model Load Time | ~5 seconds | After initial download |
| LLM Inference Time | ~3-5 seconds | Per verification plan generation |
| Snapshot Capture | ~1 second | With API or local extension |
| Authorization Check | <1ms | In-process policy evaluation |
| Total Action Loop | ~5-10 seconds | Including verification |
| Memory Usage | ~8GB | 7B model on MPS |

## Production Deployment

### Sidecar Mode

For production, use the Rust-based `predicate-authorityd` sidecar. The sidecar is **optional** but recommended for enterprise deployments.

#### Option 1: Local IdP (Demo/Testing)

```bash
# Start sidecar with local IdP mode
export LOCAL_IDP_SIGNING_KEY="your-production-secret-key"

predicate-authorityd run \
  --host 127.0.0.1 \
  --port 8787 \
  --mode local_only \
  --policy-file policies/browser_automation.yaml \
  --identity-mode local-idp \
  --local-idp-issuer "http://localhost/predicate-local-idp" \
  --local-idp-audience "api://predicate-authority"

# Verify sidecar is running
curl http://127.0.0.1:8787/health
```

#### Option 2: Bring Your Own IdP (Enterprise)

The sidecar integrates with your existing identity provider:

**Okta:**
```bash
predicate-authorityd run \
  --identity-mode oidc \
  --oidc-issuer https://your-domain.okta.com \
  --oidc-client-id <client-id> \
  --oidc-client-secret <secret> \
  --policy-file policies/browser_automation.yaml
```

**Entra ID (Azure AD):**
```bash
predicate-authorityd run \
  --identity-mode entra \
  --entra-tenant-id <tenant-id> \
  --entra-client-id <client-id> \
  --entra-client-secret <secret> \
  --policy-file policies/browser_automation.yaml
```

**Generic OIDC:**
```bash
predicate-authorityd run \
  --identity-mode oidc \
  --oidc-issuer https://your-idp.com \
  --oidc-client-id <client-id> \
  --oidc-client-secret <secret> \
  --policy-file policies/browser_automation.yaml
```

Benefits of sidecar mode:

✓ Centralized authorization across multiple agents
✓ Production-grade audit logging
✓ Hot-reload policy changes without agent restart
✓ Fleet management and monitoring
✓ Higher performance (Rust vs Python)
✓ Enterprise identity integration (Okta, Entra ID, OIDC)

### Cloud-Connected Mode

For enterprise deployments with Predicate Cloud:

```bash
export PREDICATE_API_KEY="your-api-key"

predicate-authorityd run \
  --mode cloud_connected \
  --control-plane-url https://api.predicatesystems.dev \
  --tenant-id your-tenant \
  --project-id your-project \
  --predicate-api-key $PREDICATE_API_KEY
```

This enables:
- Centralized policy management
- Real-time monitoring dashboard
- Historical audit trails
- Team collaboration on policies

## Key Takeaways

### 1. Defense in Depth
Don't rely on prompt engineering alone. Use policy-based authorization + LLM verification for robust safety.

### 2. Local LLMs Are Viable
Qwen 2.5 7B provides sufficient reasoning for verification predicates while running completely offline on consumer hardware.

### 3. Semantic Queries Beat CSS
The `find()` DSL with role-based and text-based matching is more resilient than brittle CSS selectors.

### 4. Visual Debugging Matters
Snapshot overlays that highlight detected elements make debugging agent behavior dramatically faster.

## What's Next?

We're actively developing Predicate Secure with upcoming features:

- **Multi-step verification chains** - Complex assertion flows
- **Replay killswitches** - Emergency agent shutdown
- **Vision fallback** - Handle CAPTCHAs and complex UIs
- **Permission recovery** - Graceful handling of authorization failures
- **Temporal integration** - Durable execution for long-running agents

The demo is open source and available in the [Sentience repository](https://github.com/predicatesystems/Sentience) under `predicate-secure/py-predicate-secure/demo`.

## Get Started Today

Try Predicate Secure in 5 minutes. No API key required - runs completely offline with local LLM verification.

📚 [Demo README](https://github.com/predicatesystems/Sentience/tree/main/predicate-secure/py-predicate-secure/demo/README.md)
📖 [Architecture Doc](https://github.com/predicatesystems/Sentience/tree/main/predicate-secure/py-predicate-secure/demo/ARCHITECTURE.md)
📘 [Predicate Authority User Manual](https://github.com/predicatesystems/Sentience/tree/main/AgentIdentity/docs/predicate-authority-user-manual.md)
🔧 [SDK Python Docs](https://docs.sentienceapi.com/sdk-python)

---

**Have questions or feedback?** Reach out to us on [GitHub](https://github.com/predicatesystems/Sentience/issues) or [Discord](https://discord.gg/predicate).

Built with ❤️ by the Predicate team.
