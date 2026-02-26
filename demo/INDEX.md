# Predicate Secure Demo - Documentation Index

Complete pre-execution authorization + post-execution verification demo for AI agent browser automation.

## 📚 Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[QUICKSTART.md](QUICKSTART.md)** | Get running in 5 minutes | 5 min |
| **[README.md](README.md)** | Full documentation and setup guide | 15 min |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Detailed design and architecture | 20 min |
| **[SIDECAR_SETUP.md](SIDECAR_SETUP.md)** | Optional: Production sidecar setup | 10 min |
| **[demo_summary.txt](demo_summary.txt)** | Quick reference summary | 3 min |

## 🚀 Quick Navigation

### First Time Here?
1. Start with **[QUICKSTART.md](QUICKSTART.md)** to get the demo running
2. Once it's working, read **[README.md](README.md)** for full context
3. For deep dive, read **[ARCHITECTURE.md](ARCHITECTURE.md)**

### Looking to Customize?
- **Authorization**: Edit [policies/browser_automation.yaml](policies/browser_automation.yaml)
- **Verification**: Modify [local_llm_verifier.py](local_llm_verifier.py)
- **Browser Task**: Update [secure_browser_demo.py](secure_browser_demo.py)
- **Configuration**: Edit [.env](.env)

### Troubleshooting?
- See "Troubleshooting" section in [QUICKSTART.md](QUICKSTART.md)
- Check "Configuration" section in [README.md](README.md)
- Review logs in `output/` directory

## 📂 File Overview

### Configuration Files
| File | Description |
|------|-------------|
| `.env` | Environment configuration (active) |
| `.env.example` | Environment template with documentation |
| `requirements.txt` | Python package dependencies |
| `policies/browser_automation.yaml` | Authorization policy rules |

### Source Code
| File | Description | Lines |
|------|-------------|-------|
| `secure_browser_demo.py` | Main orchestrator - runs the complete loop | ~400 |
| `local_llm_verifier.py` | Post-execution verification with Qwen 2.5 7B | ~400 |

### Documentation
| File | Description | Purpose |
|------|-------------|---------|
| `QUICKSTART.md` | 5-minute quick start | Get running fast |
| `README.md` | Full documentation | Complete guide |
| `ARCHITECTURE.md` | Architecture deep dive | Understand design |
| `INDEX.md` | This file | Navigation hub |
| `demo_summary.txt` | Quick reference | Text summary |

### Directories
| Directory | Purpose |
|-----------|---------|
| `policies/` | Authorization policy files (YAML) |
| `output/` | Runtime output (logs, videos) |

## 🎯 Core Concepts

### The Complete Loop

```
User Request
     ↓
┌─────────────────────────────────────┐
│ 1. PRE-EXECUTION AUTHORIZATION      │  ← predicate-authority + policy
│    Check: Is action allowed?        │
└─────────────┬───────────────────────┘
              ↓ ALLOWED
┌─────────────────────────────────────┐
│ 2. EXECUTE ACTION                   │  ← PredicateBrowser
│    Run: Browser operation           │
└─────────────┬───────────────────────┘
              ↓ EXECUTED
┌─────────────────────────────────────┐
│ 3. POST-EXECUTION VERIFICATION      │  ← Local LLM (Qwen 2.5 7B)
│    Verify: Did action succeed?      │
└─────────────┬───────────────────────┘
              ↓
         SUCCESS / FAILURE
```

### Key Components

1. **SecureAgent**: Wraps browser with authorization and verification
2. **Policy Engine**: Evaluates YAML rules to allow/deny actions
3. **PredicateBrowser**: Playwright-based browser automation
4. **LocalLLMVerifier**: Generates verification assertions using Qwen 2.5 7B
5. **Orchestrator**: SecureBrowserDemo class coordinates the loop

## 📖 Common Tasks

### Run the Demo
```bash
cd /Users/guoliangwang/Code/Sentience/predicate-secure/py-predicate-secure/demo
python secure_browser_demo.py
```

### Test Policy Violation
```bash
# Edit .env
DEMO_START_URL=https://malicious-site.com

# Run demo - should fail at authorization
python secure_browser_demo.py
```

### Use Smaller Model
```bash
# Edit .env
LLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct

# Run demo - uses less RAM
python secure_browser_demo.py
```

### Add Custom Verification
```python
# Edit local_llm_verifier.py
def _execute_predicate(self, predicate: str, args: list) -> bool:
    # Add your custom predicate here
    if predicate == "my_custom_check":
        # Your logic here
        return True
```

### Add Custom Policy Rule
```yaml
# Edit policies/browser_automation.yaml
rules:
  - name: my-custom-rule
    effect: ALLOW
    principals:
      - "agent:demo-browser"
    actions:
      - "browser.my_action"
    resources:
      - "https://my-domain.com*"
```

## 🔗 Related Documentation

### External References
- **Predicate Authority**: `AgentIdentity/docs/predicate-authority-user-manual.md`
- **SDK Python**: `sdk-python/README.md`
- **Predicate Secure**: `py-predicate-secure/README.md`
- **WebBench**: `webbench/README.md`

### Referenced Components
- **Sidecar**: `rust-predicate-authorityd/` (Rust)
- **Runtime SDK**: `sdk-python/predicate/browser.py`
- **Authority SDK**: `AgentIdentity/predicate_authority/`
- **Planner Agent**: `webbench/webbench/agents/planner_executor_agent.py`

## 🏗️ Extension Ideas

1. **Multi-Agent Delegation**: Pass mandates between agents
2. **Audit Trail Database**: Store decisions in PostgreSQL
3. **Real-time Monitoring**: Dashboard for authorization decisions
4. **Policy Learning**: Learn policies from human demonstrations
5. **Vision-Based Verification**: Use multimodal LLM for screenshot verification
6. **Automatic Repair**: Auto-fix actions that fail verification

## ⚠️ Important Notes

- **First Run**: Downloads Qwen 2.5 7B (~14GB), takes 2-5 minutes
- **Memory**: Requires ~8GB RAM for 7B model (use 3B if limited)
- **GPU**: Recommended but not required (works on CPU/MPS)
- **Browser**: Requires Playwright chromium installation
- **Production**: Use `predicate-authorityd` sidecar for better performance

## 🆘 Getting Help

1. Check **[QUICKSTART.md](QUICKSTART.md)** troubleshooting section
2. Review **[README.md](README.md)** configuration guide
3. Read **[ARCHITECTURE.md](ARCHITECTURE.md)** for design decisions
4. Check `output/` directory for logs
5. Create an issue in the repository

---

**Quick Links:**
- [Run Demo](#run-the-demo)
- [Documentation](#-documentation)
- [Customization](#looking-to-customize)
- [Troubleshooting](#troubleshooting)
- [Architecture](#core-concepts)
