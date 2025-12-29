# Customer Support Agent - Kurral Production Example

A production-ready customer support agent demonstrating Kurral's value for testing conversational AI systems.

## 🎯 What This Demonstrates

**Real-World Use Case:** Automated customer support with knowledge base lookup + web search

**Kurral Value Props:**
- ✅ **Deterministic Testing:** Replay exact support scenarios for regression testing
- ✅ **Cost Savings:** Test unlimited times after initial capture
- ✅ **Observability:** See every tool call, LLM interaction, decision path
- ✅ **Quality Assurance:** Validate tone, accuracy, escalation logic

## 💰 Cost Comparison

### Scenario: Testing 20 Support Conversations

**Without Kurral:**
```
20 test runs × $0.10/conversation (GPT-4o-mini) = $2.00
Regression testing weekly (4 weeks) = $8.00/month
Annual cost = $96.00
```

**With Kurral:**
```
Initial capture: 20 conversations × $0.10 = $2.00
Replay (unlimited): $0.00
Regression testing weekly = $0.00
Annual cost = $2.00  (99% savings!)
```

**ROI:** After first replay, Kurral pays for itself.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API Key

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run the Agent

```bash
# Interactive mode
python agent.py

# Example queries to try:
Customer: What are your shipping options?
Customer: How do I return an item?
Customer: I forgot my password
```

### 4. Replay for Free

```bash
# After first run, replay with zero cost
kurral replay --latest
```

## 📁 Project Structure

```
customer-support/
├── agent.py                    # Main agent (vanilla Kurral template)
├── knowledge_base/
│   └── faqs.json              # Deterministic FAQ lookup
├── tests/
│   └── test_scenarios.py      # Kurral replay tests
├── requirements.txt
├── .env.example
└── README.md
```

## 🛠️ Tools

### 1. `search_knowledge_base` (Deterministic)
- Searches local FAQ database
- **Fast:** No API calls
- **Deterministic:** Same input → same output
- **Perfect for Kurral replay!**

### 2. `web_search` (Non-Deterministic)
- Real-time web search for current info
- Order status, product availability, service status
- Kurral captures once, replays instantly

## 🧪 Testing with Kurral

### Test Scenario: Shipping Policy Changes

```python
# 1. Initial capture (pays for API)
python agent.py
> "What's your return policy?"

# 2. Update policy in knowledge_base/faqs.json

# 3. Replay to verify new responses (FREE!)
kurral replay --latest

# Agent now uses updated knowledge base, zero API cost
```

### Regression Test Suite

```bash
cd tests
pytest test_scenarios.py

# Kurral replays all 20 scenarios
# Time: ~5 seconds
# Cost: $0.00
```

## 🎓 Learning Outcomes

After running this example, you'll understand:

1. **How Kurral captures interactions** - LLM calls, tool executions, full context
2. **When replay saves money** - Repetitive testing scenarios
3. **How to build deterministic tools** - Knowledge base vs. web search tradeoffs
4. **Regression testing patterns** - Validate behavior after code/data changes

## 🔧 Customization Ideas

- Add more FAQ categories (billing, technical support, products)
- Integrate with real order tracking API
- Add sentiment analysis to detect frustrated customers
- Implement escalation logic to human agents
- Multi-language support with translation tools

## 📊 Production Considerations

**What This Example Shows:**
- Basic conversational agent structure
- Tool selection logic
- Knowledge base integration

**What Production Needs:**
- Session/conversation management
- Customer context (order history, preferences)
- Escalation workflows
- Analytics and quality metrics
- Multi-turn conversation state

## 💡 Next Steps

1. Try the **code-review-agent** example (static analysis + AI review)
2. Try the **research-assistant** example (multi-step reasoning)
3. Read the [Kurral documentation](https://github.com/Kurral/Kurralv3) for advanced features
4. Join our [Discord](https://discord.gg/pan6GRRV) to share your use case

---

**Generated from:** `kurral init` (vanilla template)
**Kurral Version:** 0.3.1+