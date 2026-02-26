# Predicate Secure Browser Automation Demo

This demo showcases the complete **pre-execution authorization + post-execution verification** loop for AI agent browser automation using:

1. **Pre-execution Authorization**: `predicate-authority` with policy-based access control
2. **Browser Automation**: `PredicateBrowser` from sdk-python
3. **Post-execution Verification**: Local LLM (Qwen 2.5 7B) generates verification assertions on-the-fly

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Secure Agent Loop                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────┐
         │  1. PRE-EXECUTION AUTHORIZATION      │
         │     (predicate-authority + policy)    │
         └──────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Authorized?     │
                    └─────────┬─────────┘
                         YES  │  NO
                    ┌─────────┴──────┐
                    │                │
                    ▼                ▼
         ┌──────────────────┐   [DENY]
         │  2. EXECUTE       │   └──────
         │     ACTION        │
         │  (PredicateBrowser)│
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────────────────────────┐
         │  3. POST-EXECUTION VERIFICATION      │
         │     (Local LLM generates assertions)  │
         └──────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │  Verify action success   │
         │  (assertions executed)    │
         └──────────────────────────┘
                    │
              ┌─────┴─────┐
              │  Passed?  │
              └─────┬─────┘
               YES  │  NO
          ┌─────────┴──────┐
          │                │
          ▼                ▼
      [SUCCESS]      [FAILED]
```

## Features

- **Policy-Based Authorization**: YAML policy file defines allowed actions, principals, resources, and required verification labels
- **Fail-Closed by Default**: All actions denied unless explicitly allowed by policy
- **Dynamic Verification**: Local LLM generates verification assertions based on action context and page state
- **Visual Element Overlay**: Watch the browser highlight detected DOM elements with colored boxes during snapshot
- **Rich Console Output**: Beautiful terminal output with real-time progress indicators
- **Audit Trail**: All authorization decisions and verification results logged

## Prerequisites

### System Requirements

- Python 3.11+
- 8GB+ RAM (for Qwen 2.5 7B model)
- CUDA-capable GPU (recommended) or CPU/MPS (Apple Silicon)
- **NO API KEY REQUIRED** - Uses free tier browser extension

### API Key (Optional)

The demo works with **FREE TIER** (local browser extension only) by default. No API key needed!

If you have a Predicate API key for enhanced features:
```bash
# In .env
PREDICATE_API_KEY=your-api-key-here
```

**Free tier is completely sufficient for this demo.** The demo works entirely offline after initial model download.

### Required Packages

Install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

**Core dependencies:**
- `predicate-secure` (from parent directory)
- `predicate` (sdk-python for browser automation)
- `predicate-authority[sidecar]` (authorization engine)
- `transformers` + `torch` (for local LLM)
- `playwright` (browser automation - installed with predicate)

## Authorization Modes

The demo supports two authorization modes:

### In-Process Mode (Default - Recommended for Demo)

**No sidecar needed!** Policy evaluation happens directly in Python.

✅ **Advantages:**
- Zero setup - just run the demo
- No additional processes to manage
- Perfect for development and testing
- Full policy support

❌ **Limitations:**
- Not suitable for multi-agent production deployments
- No centralized authorization server

### Sidecar Mode (Optional - Production Setup)

Uses the Rust-based `predicate-authorityd` sidecar for centralized authorization.

✅ **Advantages:**
- Production-grade performance
- Centralized authorization across multiple agents
- Built-in audit logging
- Fleet management support

❌ **Requirements:**
- Must install and start sidecar process
- Requires additional configuration

**See "Optional: Production Mode with Sidecar" in [QUICKSTART.md](QUICKSTART.md) for setup instructions.**

---

## Quick Start

### 1. Install Dependencies

```bash
# Navigate to predicate-secure directory
cd /path/to/predicate-secure/py-predicate-secure

# Install predicate-secure SDK
pip install -e .

# Install demo dependencies (includes predicate-runtime==1.1.2 from PyPI)
cd demo
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Download LLM Model (First Run Only)

On first run, the demo will automatically download the Qwen 2.5 7B model from HuggingFace (~14GB).

To pre-download:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    trust_remote_code=True
)
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your preferences
nano .env
```

**Key settings:**

```bash
# Browser display (false = show browser, true = headless)
BROWSER_HEADLESS=false

# LLM model (default: Qwen 2.5 7B)
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
LLM_DEVICE=auto  # auto, cuda, cpu, mps

# Demo task
DEMO_START_URL=https://www.example.com
DEMO_TASK_DESCRIPTION=Navigate to example.com and verify page loads
```

### 4. Run the Demo

```bash
python secure_browser_demo.py
```

**Expected output:**

```
╭──────────── Demo Configuration ─────────────╮
│ Predicate Secure Browser Automation Demo   │
│                                             │
│ Task: Navigate to example.com and verify   │
│ Start URL: https://www.example.com         │
│ Principal: agent:demo-browser              │
╰─────────────────────────────────────────────╯

Initializing Local LLM Verifier...
⠋ Loading Qwen 2.5 7B model...
✓ Verifier initialized

Initializing Secure Agent...
✓ SecureAgent initialized
  Policy: demo/policies/browser_automation.yaml
  Mode: strict (fail-closed)
  Principal: agent:demo-browser

Step 1: Initializing Browser...
✓ Browser started

Step 2: Executing Browser Task...

→ Action: navigate (https://www.example.com)
  Pre-execution: Checking authorization...
  ✓ Action authorized
  Executing action...
  ✓ Action executed
  Post-execution: Generating verification plan...
  i Generated 2 verifications
    Reasoning: Verify navigation succeeded and page loaded
  Executing verifications...
    [1] url_contains(example.com)
        ✓ Passed
    [2] snapshot_changed()
        ✓ Passed
  ✓ All verifications passed

→ Action: snapshot (current_page)
  Pre-execution: Checking authorization...
  ✓ Action authorized
  Executing action...
    Snapshot captured: 42 elements
  ✓ Action executed
  Post-execution: Generating verification plan...
  i Generated 1 verifications
  Executing verifications...
    [1] element_count(body, 1)
        ✓ Passed
  ✓ All verifications passed

✓ Task completed successfully

╭─────── Success ───────╮
│ ✓ Demo completed      │
│   successfully!       │
╰───────────────────────╯
```

## Project Structure

```
demo/
├── README.md                          # This file
├── .env.example                       # Environment template
├── requirements.txt                   # Python dependencies
├── policies/
│   └── browser_automation.yaml        # Authorization policy
├── output/                            # Output directory (created automatically)
│   ├── logs/                          # Execution logs
│   └── videos/                        # Browser recordings (if enabled)
├── local_llm_verifier.py              # Local LLM verification planner
└── secure_browser_demo.py             # Main demo script
```

## Configuration

### Policy File (`policies/browser_automation.yaml`)

The policy file defines authorization rules:

```yaml
rules:
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

  # Block dangerous domains
  - name: block-dangerous-domains
    effect: DENY
    principals:
      - "*"
    actions:
      - "browser.navigate"
    resources:
      - "http://*"  # Force HTTPS
      - "file://*"
      - "javascript:*"
```

**Policy components:**
- **principals**: Who can perform the action (agent identities)
- **actions**: What actions are allowed/denied
- **resources**: Which targets (URLs, elements) are allowed
- **conditions**: Required labels and verification signals

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BROWSER_HEADLESS` | `false` | Run browser in headless mode |
| `LLM_MODEL_NAME` | `Qwen/Qwen2.5-7B-Instruct` | HuggingFace model for verification |
| `LLM_DEVICE` | `auto` | Device: `auto`, `cuda`, `cpu`, `mps` |
| `LLM_MAX_TOKENS` | `512` | Max tokens for LLM generation |
| `DEMO_START_URL` | `https://www.example.com` | Starting URL for task |
| `DEMO_PRINCIPAL_ID` | `agent:demo-browser` | Agent identity |

## Advanced Usage

### Custom Tasks

Modify the demo script to run custom browser tasks:

```python
# In secure_browser_demo.py, modify _run_browser_task()

async def _run_browser_task(self):
    """Custom browser task."""

    # Navigate to search page
    await self._authorized_action(
        action="navigate",
        target="https://www.google.com",
        executor=lambda: self.browser.goto("https://www.google.com")
    )

    # Click search box
    await self._authorized_action(
        action="click",
        target="input[name=q]",
        executor=lambda: self.browser.page.click("input[name=q]")
    )

    # Type search query
    await self._authorized_action(
        action="type",
        target="input[name=q]",
        executor=lambda: self.browser.page.fill("input[name=q]", "predicate systems")
    )
```

### Using the Sidecar (Production)

For production deployments, use the `predicate-authorityd` sidecar:

```bash
# Start sidecar with local-idp mode
export LOCAL_IDP_SIGNING_KEY="your-strong-secret-key"

predicate-authorityd run \
  --host 127.0.0.1 \
  --port 8787 \
  --mode local_only \
  --policy-file demo/policies/browser_automation.yaml \
  --identity-mode local-idp \
  --local-idp-issuer "http://localhost/predicate-local-idp" \
  --local-idp-audience "api://predicate-authority"
```

Then connect SecureAgent to the sidecar:

```python
from predicate_secure import SecureAgent

secure_agent = SecureAgent(
    agent=browser_config,
    sidecar_url="http://127.0.0.1:8787",  # Connect to sidecar
    principal_id="agent:demo-browser",
    mode="strict"
)
```

### Custom Verification Logic

Extend `LocalLLMVerifier` with custom predicates:

```python
# In local_llm_verifier.py, add to _execute_predicate()

def _execute_predicate(self, predicate: str, args: list) -> bool:
    # ... existing predicates ...

    elif predicate == "form_submitted":
        # Custom predicate: check if form was submitted
        return self.browser.page.url != self.pre_action_url

    elif predicate == "toast_visible":
        # Custom predicate: check for success toast
        toast_text = args[0] if args else "Success"
        return toast_text in self.browser.page.inner_text(".toast")
```

## Troubleshooting

### Model Loading Errors

**Issue:** OOM (Out of Memory) when loading Qwen 2.5 7B

**Solution:** Use a smaller model or enable quantization:

```bash
# Use smaller model (3B)
export LLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct

# Or enable 8-bit quantization (requires bitsandbytes)
pip install bitsandbytes
# Modify local_llm_verifier.py to enable load_in_8bit=True
```

### Browser Launch Errors

**Issue:** Browser fails to start

**Solution:** Ensure Playwright browsers are installed:

```bash
playwright install chromium
```

### Policy Violations

**Issue:** Actions denied by policy

**Solution:** Check policy file and add appropriate allow rules:

```yaml
# Add to policies/browser_automation.yaml
- name: allow-your-domain
  effect: ALLOW
  principals:
    - "agent:demo-browser"
  actions:
    - "browser.navigate"
  resources:
    - "https://your-domain.com*"
```

## Next Steps

1. **Add More Predicates**: Extend verification predicates in `local_llm_verifier.py`
2. **Connect to Sidecar**: Use production `predicate-authorityd` sidecar for centralized authorization
3. **Add Audit Trail**: Store authorization decisions and verification results in database
4. **Multi-Agent Scenarios**: Test delegation and mandate passing between agents
5. **Production Policies**: Create comprehensive policies for production workloads

## References

- **predicate-authority User Manual**: `/Users/guoliangwang/Code/Sentience/AgentIdentity/docs/predicate-authority-user-manual.md`
- **sdk-python Documentation**: `/Users/guoliangwang/Code/Sentience/sdk-python/README.md`
- **predicate-secure Documentation**: `/Users/guoliangwang/Code/Sentience/predicate-secure/py-predicate-secure/README.md`

## Support

For issues or questions, create an issue in the repository or contact the Predicate Systems team.
