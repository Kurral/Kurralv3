# Kurral Production Examples

Three complete, production-ready agent examples demonstrating Kurral's value across different use cases.

## 🎯 Examples Overview

### 1. [Customer Support Agent](./customer-support/) ⭐ Start Here

**Use Case:** Automated customer service with FAQ lookup and web search

**Why This Example:**
- Most universally relatable use case
- Clear cost savings demonstration (99% reduction)
- Shows deterministic vs. non-deterministic tools
- Perfect introduction to Kurral's testing workflow

**Key Learnings:**
- How Kurral captures and replays conversations
- When to use deterministic tools (knowledge base)
- Cost-effective regression testing
- Quality assurance for conversational AI

**Time to Run:** 5 minutes
**Cost Savings:** $96/year → $2/year

---

### 2. [Code Review Agent](./code-review/)

**Use Case:** AI-powered code reviewer with security checks and style suggestions

**Why This Example:**
- Shows file system integration
- Demonstrates pattern matching and analysis
- Testing review logic changes
- Comparing review quality across models

**Key Learnings:**
- File-based agent workflows
- Security pattern detection
- Regression testing code analysis
- Model comparison strategies

**Time to Run:** 10 minutes
**Cost Savings:** $390/year → $7.50/year

---

### 3. [Research Assistant](./research-assistant/)

**Use Case:** Multi-step research with source aggregation and summarization

**Why This Example:**
- Complex multi-step reasoning
- Source selection and ranking
- Citation management
- Research workflow optimization

**Key Learnings:**
- Multi-step agent patterns
- Source credibility evaluation
- Information synthesis
- Testing research strategies

**Time to Run:** 15 minutes
**Cost Savings:** $20/month → $5/month

---

## 🚀 Getting Started

### Prerequisites

```bash
# Install Kurral
pip install kurral[mcp]

# Generate your own agent (optional)
kurral init my-agent
```

### Run an Example

```bash
# 1. Choose an example
cd customer-support/

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 4. Run the agent
python agent.py

# 5. Replay for free!
kurral replay --latest
```

## 💡 Common Patterns

All three examples demonstrate:

1. **Vanilla Python Template** - No framework lock-in
2. **Minimal Dependencies** - `openai`, `python-dotenv`, `kurral`
3. **Explicit Agent Loop** - See exactly what's happening
4. **Mixed Tool Types** - Deterministic + non-deterministic
5. **Cost-Effective Testing** - Capture once, replay unlimited

## 📊 Cost Comparison Summary

| Example | Use Case | Without Kurral | With Kurral | Savings |
|---------|----------|----------------|-------------|---------|
| Customer Support | 20 scenarios/week | $96/year | $2/year | 98% |
| Code Review | 50 files/week | $390/year | $7.50/year | 98% |
| Research | 10 queries/month | $20/month | $5/month | 75% |

**Total Annual Savings:** **$498/year** for these three use cases alone!

## 🎓 Learning Path

**New to Kurral?** Follow this path:

1. **Start:** Customer Support (easiest, most relatable)
2. **Next:** Code Review (file system + analysis patterns)
3. **Advanced:** Research Assistant (multi-step reasoning)

Each example builds on concepts from the previous one.

## 🔧 Customization

All examples are fully functional starting points. Common customizations:

- **Add Your Tools:** Each example uses vanilla template - easy to extend
- **Change LLM:** Switch models by changing `--model` flag
- **Add Tests:** Expand test scenarios in `tests/`
- **Production Deploy:** Add auth, rate limiting, monitoring

## 📖 Next Steps

After running these examples:

1. **Read the docs:** [Kurral GitHub](https://github.com/Kurral/Kurralv3)
2. **Join Discord:** [Community](https://discord.gg/pan6GRRV)
3. **Build your agent:** `kurral init your-use-case`
4. **Share your results:** We love hearing about your use cases!

## 🤝 Contributing

Found a bug? Have an idea for another example? PRs welcome!

- Add new example use cases
- Improve existing examples
- Fix bugs or typos
- Enhance documentation

---

**Generated with:** `kurral init` (vanilla template)
**Framework:** None (pure Python)
**Kurral Version:** 0.3.1+
