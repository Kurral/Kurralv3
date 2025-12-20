# Research Assistant - Kurral Production Example

Multi-step research agent demonstrating Kurral's value for complex reasoning workflows.

## 🎯 What This Demonstrates

**Use Case:** Multi-step research with web search, source aggregation, and summarization

**Kurral Value:**
- Test multi-step reasoning logic without API costs
- Validate source selection and ranking
- Regression test summarization quality
- Compare research strategies across models

## 💰 Cost Savings

Testing research workflow for 10 different queries:
- **Without Kurral:** 10 queries × $0.50/query (multi-step) = $5.00 per test
- **With Kurral:** Initial capture $5.00, unlimited replays = $0

Monthly testing (4 iterations): **$20 → $5** (75% savings)

## 🚀 Quick Start

```bash
# Install
pip install -r requirements.txt
cp .env.example .env

# Research a topic
python agent.py

# Example query:
> "What are the latest developments in quantum computing?"

# Replay for free
kurral replay --latest
```

## 🧠 Research Process

1. **Query Analysis** - Break down research question
2. **Web Search** - Find relevant sources (3-5 results per sub-query)
3. **Source Ranking** - Prioritize credible, recent sources
4. **Information Extraction** - Pull key facts and quotes
5. **Synthesis** - Combine into coherent summary with citations

## 📊 Example Output

```
Research Summary: Quantum Computing Developments

Key Findings:
1. IBM achieved 127-qubit quantum processor (Nov 2023)
2. Google demonstrated quantum error correction breakthrough
3. Commercial quantum cloud services expanding (AWS, Azure, IBM)

Sources:
- Nature: "Quantum Error Correction..." (2023-11-15)
- MIT Tech Review: "IBM's Quantum Roadmap" (2023-10-20)
- ArXiv: "Advances in Quantum Algorithms" (2023-09-30)

Confidence: High (3 corroborating sources from credible publishers)
```

---

**Generated from:** `kurral init` (vanilla template)
