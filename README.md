<p align="center">
  <img width="350" height="350" alt="Kurral Logo" src="assets/4c469b1e-6cc4-479e-b18a-16a9cb214d8e.png" />
</p>

<h1 align="center">KURRAL</h1>
<h3 align="center">MCP Security, Observability & Deterministic Testing Platform</h3>
<p align="center">Secure, observe, and reliably test Model Context Protocol (MCP) deployments and AI agents</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/kurral" alt="PyPI" />
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.9+-blue" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/MCP-Security_Ready-orange" alt="MCP Security" />
  <img src="https://img.shields.io/badge/SAFE--MCP-Compatible-green" alt="SAFE-MCP" />
  <img src="https://img.shields.io/badge/LangChain-Compatible-green" alt="LangChain Compatible" />
</p>

<p align="center">
  ⭐ If Kurral saves you hours (or dollars), please <a href="https://github.com/kurral/kurralv3">star the repo</a> — it helps a lot!
</p>

---

## 🎯 The Growing MCP & Agent Challenge

Model Context Protocol (MCP) is rapidly becoming the standard for AI agent tool integration — adopted by Anthropic, OpenAI, Google, Microsoft and others. Yet enterprises face critical hurdles before full adoption:

- **🔍 Visibility** – What tools are agents calling? What data is flowing?
- **🛡️ Security** – Are MCP servers vulnerable to tool poisoning, prompt injection, or data exfiltration?
- **🧪 Reliable Testing** – How to test agents deterministically without unpredictable outputs or massive API costs?

**Kurral delivers all three:** observability and testing today, automated security testing in Q1 2026.

---

## 🚀 Three Core Pillars

### 1. MCP Observability ✅ Available Now

**Full HTTP/SSE proxy with complete traffic visibility and replay**

```bash
pip install kurral[mcp]
kurral mcp start --mode record                           # Capture everything
kurral mcp export -o session.kurral                      # Export artifact
kurral mcp start --mode replay --artifact session.kurral # Replay offline
```

**Capabilities:**
- ✅ Capture & replay all MCP tool calls with full SSE streaming
- ✅ Performance metrics (duration, TTFE, event rates)
- ✅ Multi-server routing & semantic tool matching
- ✅ Shareable .kurral artifacts for debugging

**Use Cases:** Production issue reproduction, cost-free development, team collaboration.

**📖 [Full MCP Proxy Documentation →](MCP_PROXY_README.md)**

---

### 2. Deterministic Agent Testing ✅ Available Now

**Intelligent capture & replay for regression testing and A/B comparison**

```python
from kurral import trace_agent, trace_agent_invoke

@trace_agent()
def main():
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    agent_executor = AgentExecutor(agent=agent, tools=tools)

    result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
    return result
```

**Intelligent Replay:**
- **A Replay (Deterministic)**: High config similarity → cached outputs, zero API cost
- **B Replay (Exploratory)**: Changes detected → re-execute LLM with semantic tool caching

**Agent Regression Score (ARS):**
```
ARS = (Output Similarity × 0.7) + (Tool Accuracy × 0.3)
```
Penalties for new/unused tools. Perfect for CI/CD thresholds.

**Side Effect Protection:** Auto-generates config, requires manual review before replay.

**Use Cases:**
- ✅ Regression testing & CI/CD
- ✅ Model upgrades (GPT-4o vs. newer models)
- ✅ Prompt engineering comparisons
- ✅ 99% API cost reduction in testing

**📖 [Deep Dive: How Replay Works →](REPLAY_DEEP_DIVE.md)**

---

### 3. MCP Security Testing 🚧 Phase 1: Q1 2026

**Automated testing against the SAFE-MCP threat framework**

Kurral will systematically test deployments against critical MCP attacks:

**Phase 1 (Q1 2026):**
- ✅ **T1001** Tool Poisoning
- ✅ **T1102** Prompt Injection
- ✅ **T1201** MCP Rug Pull
- ✅ Cross-Tool Shadowing
- ✅ Data Exfiltration
- ✅ Unauthorized Tool Execution
- ✅ Malicious Server Distribution

```bash
kurral security test baseline.kurral --techniques T1001,T1102
```

**Deliverables:**
- 50–70 attack variants tested
- Detailed PDF/JSON reports with severity, findings & remediation
- Baseline vs. attack comparison

**📖 [Security Roadmap & Details →](MCP_SECURITY_ROADMAP.md)**

---

## 📦 Installation

```bash
pip install kurral                # Core testing
pip install kurral[mcp]           # + MCP proxy & observability
```

**From source:**
```bash
git clone https://github.com/kurral/kurralv3.git
cd kurralv3
pip install -e ".[mcp]"
```

---

## 🎬 Quick Start: MCP Observability

```bash
kurral mcp init                     # Generate config
kurral mcp start --mode record      # Proxy runs on localhost:3100
# Point your agent to http://localhost:3100
kurral mcp export -o session.kurral
kurral mcp start --mode replay --artifact session.kurral
```

**📖 [Full MCP Proxy Guide →](MCP_PROXY_README.md)**

---

## 🎬 Quick Start: Agent Testing

```python
from kurral import trace_agent, trace_agent_invoke

@trace_agent()
def main():
    # Your agent setup...
    result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
    print(result['output'])
```

Run → artifact saved automatically.

First replay triggers auto-generation of `side_effect/side_effects.yaml` with smart suggestions. Review and set `done: true`.

Then replay:
```bash
kurral replay --latest
# or
kurral replay <kurral_id>
```

Detailed output includes replay type, ARS score, cache hits, and changes detected.

**📖 [Deep Dive: Replay System →](REPLAY_DEEP_DIVE.md)**

---

## 🗄️ Storage Options

**Local (default)** → `artifacts/` and `replay_runs/`

**Cloud (R2/S3-compatible)** → scalable, team-shared artifacts

```python
from kurral import configure

configure(
    storage_backend="r2",
    r2_account_id="...",
    r2_bucket_name="kurral-artifacts"
)
```

---

## 📚 Real-World Use Cases

### Development Debugging
Customer shares .kurral artifact → You replay exact session locally → See exactly what they saw

### CI/CD Regression Testing
Capture golden path → Run tests against artifact → Fail build if ARS < 0.8 → Zero API costs

### Model Upgrade Testing
Run baseline with GPT-4 → Change to GPT-4.5 → Replay with new model → Get quantitative ARS comparison

### Cost Reduction
100 test runs/day without Kurral: $50/day = $1,000/month
With Kurral (record once, replay 99 times): $0.50/day = $10/month
**Savings: $990/month (99% reduction)**

---

## 🛣️ Roadmap

- ✅ **Now**: MCP observability, deterministic testing, intelligent replay
- 🚧 **Q1 2026**: Phase 1 MCP security testing (7 critical threats)
- 🔮 **Q2 2026+**: Full SAFE-MCP coverage, policy engine, continuous monitoring

**📖 [Security Roadmap →](MCP_SECURITY_ROADMAP.md)**

---

## ⚠️ Current Limitations

- ReAct & LCEL agents fully supported (LangGraph streaming coming soon)
- Vision inputs not yet captured
- Security testing in active development

---

## 🏗️ Architecture

**Core Components:**
- `trace_agent` - Decorator for agent main function
- `trace_agent_invoke` - Wrapper for capturing traces
- `replay` - Replay engine with A/B detection
- `ars_scorer` - Agent Regression Score calculation
- `side_effect_config` - Side effect management

**MCP Components:**
- `KurralMCPProxy` - FastAPI HTTP/SSE proxy
- `MCPCaptureEngine` - Traffic capture to artifacts
- `MCPReplayEngine` - Cached response replay
- `MCPRouter` - Multi-server routing

**📖 [Detailed Architecture →](REPLAY_DEEP_DIVE.md)**

---

## 💬 Community & Contribution

- **Discord**: [https://discord.gg/pan6GRRV](https://discord.gg/pan6GRRV)
- **Issues**: [github.com/kurral/kurralv3/issues](https://github.com/kurral/kurralv3/issues)
- **Email**: team@kurral.com

Contributions welcome — fork, branch, PR!

---

## 📝 License

Apache 2.0 - see [LICENSE](LICENSE) for details.

---

## 🌟 Why Kurral?

MCP is becoming the standard for AI tool integration. As adoption accelerates, enterprises need:

1. **Visibility** into what tools agents are calling
2. **Security** assurance that MCP servers aren't compromised
3. **Testing** capabilities that don't require expensive API calls

Kurral provides all three in one platform.

**Built for the MCP community.** If this solves a problem for you, please star the repo and join our Discord!

---

<p align="center">
  <strong>Ready to secure, observe, and reliably test your MCP agents?</strong><br>
  <code>pip install kurral[mcp]</code>
</p>
